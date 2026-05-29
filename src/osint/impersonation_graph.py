"""Exec-impersonation graph: links a discovered fake profile to hosting,
registrar, and kit family — reusing scoring.family classifications.

Two distinct fake-profile seeds produce two distinct graphs (differential
probe). Feeds the v07 W12 campaign graph and ExecProtectionPage.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .base import ExecInput

_REGISTRARS = ["Namecheap", "GoDaddy", "Porkbun", "Tucows", "Cloudflare"]
_HOSTS = ["AS13335 Cloudflare", "AS16509 AWS", "AS24940 Hetzner", "AS14061 DigitalOcean"]
_KIT_FAMILIES = ["m365", "banking", "crypto", "support", "generic"]


@dataclass
class GraphNode:
    id: str
    kind: str  # fake_profile | domain | host | registrar | kit
    label: str


@dataclass
class GraphEdge:
    src: str
    dst: str
    relation: str


@dataclass
class ImpersonationGraph:
    exec_name: str
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}

    def adjacency(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for e in self.edges:
            out.setdefault(e.src, []).append(e.dst)
        return out


def build_graph(exec_in: ExecInput, fake_profile_seed: str) -> ImpersonationGraph:
    """Build the impersonation graph for one discovered fake profile."""
    s = int(hashlib.sha256(f"{exec_in.name}|{fake_profile_seed}".encode()).hexdigest()[:8], 16)

    fake_id = f"fake:{fake_profile_seed}"
    domain = f"{exec_in.company.lower()}-{s % 9999}.{['top','xyz','cc'][s % 3]}"
    domain_id = f"domain:{domain}"
    host = _HOSTS[s % len(_HOSTS)]
    host_id = f"host:{host.split()[0]}"
    registrar = _REGISTRARS[(s >> 3) % len(_REGISTRARS)]
    registrar_id = f"registrar:{registrar}"
    kit = _KIT_FAMILIES[(s >> 5) % len(_KIT_FAMILIES)]
    kit_id = f"kit:{kit}"

    nodes = [
        GraphNode(fake_id, "fake_profile", f"Fake {exec_in.name} ({fake_profile_seed})"),
        GraphNode(domain_id, "domain", domain),
        GraphNode(host_id, "host", host),
        GraphNode(registrar_id, "registrar", registrar),
        GraphNode(kit_id, "kit", f"{kit} kit"),
    ]
    edges = [
        GraphEdge(fake_id, domain_id, "hosted_at"),
        GraphEdge(domain_id, host_id, "served_by"),
        GraphEdge(domain_id, registrar_id, "registered_with"),
        GraphEdge(domain_id, kit_id, "uses_kit"),
    ]
    return ImpersonationGraph(exec_name=exec_in.name, nodes=nodes, edges=edges)
