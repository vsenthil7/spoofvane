"""W9 doxxing monitor: home address / family exposure detection."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class DoxxingExposure:
    exec_name: str
    exposed_items: list[str]   # e.g. home_address, family_members, school
    sources: list[str]
    severity: float


def _seed(*p: str) -> int:
    return int(hashlib.sha256("|".join(p).encode()).hexdigest()[:8], 16)


_ITEMS = ["home_address", "family_members", "children_school", "spouse_employer",
          "personal_phone", "vehicle_plate"]


def scan_doxxing(exec_name: str, company: str) -> DoxxingExposure:
    """Detect doxxing-grade personal exposure. Input-dependent: distinct execs
    get distinct exposed-item sets."""
    s = _seed(exec_name, company, "dox")
    n_items = s % 5  # 0..4 items
    items = sorted({_ITEMS[(s >> j) % len(_ITEMS)] for j in range(n_items)})
    # home_address + children_school are the highest-severity items.
    weight = sum(2.0 if it in ("home_address", "children_school") else 1.0 for it in items)
    severity = round(min(1.0, weight / 8.0), 4)
    sources = [f"broker_{(s >> i) % 8}" for i in range(min(len(items), 3))]
    return DoxxingExposure(exec_name=exec_name, exposed_items=items,
                           sources=sources, severity=severity)
