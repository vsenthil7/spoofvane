"""W12 campaign detector: groups findings that share infrastructure.

Two fake domains sharing a TLS cert + kit family collapse into one campaign;
an unrelated domain stays separate. Uses a union-find over shared infra nodes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .entity_model import NodeType, Finding
from .edge_builder import Graph, build_graph

# Infra node types whose sharing implies the same campaign.
_LINKING_TYPES = {NodeType.CERT, NodeType.KIT, NodeType.IP, NodeType.ASN,
                  NodeType.REGISTRAR, NodeType.ACTOR}


@dataclass
class Campaign:
    campaign_id: str
    domains: list[str]
    shared_infra: list[str]
    finding_count: int


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def detect_campaigns(findings: list[Finding]) -> list[Campaign]:
    g = build_graph(findings)
    uf = _UnionFind()
    # Union any two domains that share a linking-infra neighbor.
    infra_to_domains: dict[str, list[str]] = {}
    for nid, node in g.nodes.items():
        if node.type == NodeType.DOMAIN:
            uf.find(nid)
            for nb in g.neighbors(nid):
                nb_node = g.nodes.get(nb)
                if nb_node and nb_node.type in _LINKING_TYPES:
                    infra_to_domains.setdefault(nb, []).append(nid)
    for infra, domains in infra_to_domains.items():
        for d in domains[1:]:
            uf.union(domains[0], d)

    # Group domains by union-find root.
    groups: dict[str, list[str]] = {}
    for nid, node in g.nodes.items():
        if node.type == NodeType.DOMAIN:
            groups.setdefault(uf.find(nid), []).append(nid)

    campaigns: list[Campaign] = []
    for i, (root, domains) in enumerate(sorted(groups.items()), 1):
        shared = sorted({
            infra for infra, ds in infra_to_domains.items()
            if any(d in domains for d in ds) and len(ds) > 1
        })
        fc = sum(1 for f in findings if f.domain and f"domain:{f.domain}" in domains)
        campaigns.append(Campaign(
            campaign_id=f"campaign_{i}",
            domains=sorted(d.split(":", 1)[1] for d in domains),
            shared_infra=shared,
            finding_count=fc,
        ))
    campaigns.sort(key=lambda c: len(c.domains), reverse=True)
    return campaigns
