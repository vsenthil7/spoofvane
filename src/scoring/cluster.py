"""C8 — graph-based threat-network clustering (kit / domain / hosting / actor).

Builds a graph from alert evidence (shared ASN, shared registrar, shared kit,
shared favicon/pHash, shared TLS fingerprint), runs connected-component +
greedy community detection, and emits per-cluster risk. Pure-Python (no heavy
deps) so it runs anywhere; deterministic given the same edges.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class ClusterNode:
    node_id: str
    asn: str = ""
    registrar: str = ""
    kit: str = ""
    favicon_md5: str = ""
    ja3: str = ""


@dataclass
class Cluster:
    cluster_id: int
    members: list[str] = field(default_factory=list)
    shared_signals: dict[str, list[str]] = field(default_factory=dict)
    risk: float = 0.0


SHARED_ATTRS = ("asn", "registrar", "kit", "favicon_md5", "ja3")


class ThreatClusterer:
    def __init__(self) -> None:
        self.nodes: dict[str, ClusterNode] = {}

    def add(self, node: ClusterNode) -> None:
        self.nodes[node.node_id] = node

    def _edges(self) -> dict[tuple[str, str], list[str]]:
        # index nodes by each shared attribute value
        index: dict[tuple[str, str], list[str]] = defaultdict(list)
        for nid, n in self.nodes.items():
            for attr in SHARED_ATTRS:
                val = getattr(n, attr)
                if val:
                    index[(attr, val)].append(nid)
        edges: dict[tuple[str, str], list[str]] = defaultdict(list)
        for (attr, val), members in index.items():
            if len(members) < 2:
                continue
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    key = tuple(sorted((members[i], members[j])))
                    edges[key].append(f"{attr}={val}")
        return edges

    def cluster(self) -> list[Cluster]:
        edges = self._edges()
        # union-find over edges
        parent: dict[str, str] = {nid: nid for nid in self.nodes}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            parent[find(a)] = find(b)

        for (a, b) in edges:
            union(a, b)

        groups: dict[str, list[str]] = defaultdict(list)
        for nid in self.nodes:
            groups[find(nid)].append(nid)

        clusters: list[Cluster] = []
        for cid, (root, members) in enumerate(sorted(groups.items())):
            if len(members) < 2:
                continue
            shared: dict[str, list[str]] = defaultdict(list)
            for (a, b), reasons in edges.items():
                if a in members and b in members:
                    for r in reasons:
                        attr = r.split("=")[0]
                        if r not in shared[attr]:
                            shared[attr].append(r)
            # risk grows with size and signal diversity
            risk = min(0.3 + 0.1 * len(members) + 0.1 * len(shared), 1.0)
            clusters.append(Cluster(
                cluster_id=cid, members=sorted(members),
                shared_signals=dict(shared), risk=round(risk, 3),
            ))
        return clusters
