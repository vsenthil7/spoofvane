"""W12 edge builder: ingests cross-surface findings and links shared infra."""
from __future__ import annotations

from dataclasses import dataclass, field

from .entity_model import Node, Edge, NodeType, Finding


@dataclass
class Graph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    _edge_keys: set = field(default_factory=set)

    def add_node(self, node: Node) -> str:
        self.nodes[node.id] = node
        return node.id

    def add_edge(self, src: str, dst: str, relation: str) -> None:
        e = Edge(src, dst, relation)
        if e.key() not in self._edge_keys:
            self._edge_keys.add(e.key())
            self.edges.append(e)

    def neighbors(self, node_id: str) -> list[str]:
        out: list[str] = []
        for e in self.edges:
            if e.src == node_id:
                out.append(e.dst)
            elif e.dst == node_id:
                out.append(e.src)
        return sorted(set(out))

    def node_ids(self) -> set[str]:
        return set(self.nodes)


class EdgeBuilder:
    # Maps a Finding attribute to (NodeType, relation from the domain/anchor).
    _ATTR_MAP = [
        ("ip", NodeType.IP, "resolves_to"),
        ("cert_sha", NodeType.CERT, "presents_cert"),
        ("asn", NodeType.ASN, "hosted_in_asn"),
        ("registrar", NodeType.REGISTRAR, "registered_with"),
        ("kit_family", NodeType.KIT, "uses_kit"),
        ("social_handle", NodeType.SOCIAL, "linked_social"),
        ("app_id", NodeType.APP, "linked_app"),
        ("actor", NodeType.ACTOR, "attributed_to"),
        ("victim_cluster", NodeType.VICTIM, "targets"),
    ]

    def build(self, findings: list[Finding]) -> Graph:
        g = Graph()
        for f in findings:
            # The anchor is the domain when present, else the first available id.
            if f.domain:
                anchor = g.add_node(Node(NodeType.DOMAIN, f.domain))
            elif f.social_handle:
                anchor = g.add_node(Node(NodeType.SOCIAL, f.social_handle))
            elif f.app_id:
                anchor = g.add_node(Node(NodeType.APP, f.app_id))
            else:
                continue
            for attr, ntype, rel in self._ATTR_MAP:
                val = getattr(f, attr)
                if val and not (attr in ("social_handle", "app_id") and
                                g.nodes.get(anchor) and g.nodes[anchor].type == ntype):
                    nid = g.add_node(Node(ntype, str(val)))
                    if nid != anchor:
                        g.add_edge(anchor, nid, rel)
        return g


def build_graph(findings: list[Finding]) -> Graph:
    return EdgeBuilder().build(findings)
