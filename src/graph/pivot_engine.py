"""W12 pivot engine: 'show everything linked to this entity' (analyst pivot)."""
from __future__ import annotations

from .edge_builder import Graph


def pivot(graph: "Graph", node_id: str, depth: int = 2) -> dict:
    """Return all entities within `depth` hops of node_id (BFS). Answers
    'show everything linked to this cert/registrar/kit'."""
    if node_id not in graph.nodes:
        return {"root": node_id, "found": [], "edges": []}
    seen = {node_id}
    frontier = [node_id]
    for _ in range(depth):
        nxt: list[str] = []
        for n in frontier:
            for nb in graph.neighbors(n):
                if nb not in seen:
                    seen.add(nb)
                    nxt.append(nb)
        frontier = nxt
        if not frontier:
            break
    linked = sorted(seen - {node_id})
    edges = [
        {"src": e.src, "dst": e.dst, "relation": e.relation}
        for e in graph.edges if e.src in seen and e.dst in seen
    ]
    return {"root": node_id, "found": linked, "edges": edges}
