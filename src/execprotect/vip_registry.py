"""W9 VIP registry: managed protectee list."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Protectee:
    name: str
    company: str
    role: str
    tier: str            # board | c_suite | vip
    monitor_physical: bool = True
    monitor_family: bool = True


@dataclass
class VipRegistry:
    _protectees: dict[str, Protectee] = field(default_factory=dict)

    def add(self, p: Protectee) -> None:
        self._protectees[p.name.lower()] = p

    def get(self, name: str) -> Protectee | None:
        return self._protectees.get(name.lower())

    def all(self) -> list[Protectee]:
        return sorted(self._protectees.values(), key=lambda p: p.name)

    def by_tier(self, tier: str) -> list[Protectee]:
        return [p for p in self._protectees.values() if p.tier == tier]
