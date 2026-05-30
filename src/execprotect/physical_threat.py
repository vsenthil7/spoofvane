"""W9 physical-threat monitor: geotagged threat mentions (ZeroFox physical
parity, fixture-backed)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
import os


@dataclass
class PhysicalThreat:
    exec_name: str
    location: str
    snippet: str
    severity: float
    source: str


def _seed(*p: str) -> int:
    return int(hashlib.sha256("|".join(p).encode()).hexdigest()[:8], 16)


def scan_physical_threats(exec_name: str, company: str) -> list[PhysicalThreat]:
    """Find geotagged threat mentions for an exec. Input-dependent; live feed
    collection is BLOCKED-ENV."""
    if os.getenv("SPOOFVANE_BD_MODE", "replay").lower() == "live":  # pragma: no cover
        raise NotImplementedError(
            "live physical-threat feeds need commercial access (BLOCKED-ENV)")
    s = _seed(exec_name, company, "phys")
    n = s % 3  # 0..2 threats
    locs = ["HQ campus", "home neighborhood", "conference venue", "airport"]
    out: list[PhysicalThreat] = []
    for i in range(n):
        si = _seed(exec_name, company, "phys", str(i))
        out.append(PhysicalThreat(
            exec_name=exec_name,
            location=locs[si % len(locs)],
            snippet=f"[synthetic] geotagged mention near {locs[si % len(locs)]}",
            severity=round(0.3 + (si % 7) / 10, 4),
            source=["social", "forum", "paste"][si % 3],
        ))
    out.sort(key=lambda t: t.severity, reverse=True)
    return out
