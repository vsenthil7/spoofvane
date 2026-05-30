"""W8 victim tracker: per-victim/per-cluster aggregation (attack magnitude).

Two victims on the same fake URL aggregate into one incident with count=2
(Memcyco "attack magnitude").
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .beacon_ingest import BeaconEvent


@dataclass
class Incident:
    cluster: str
    origin: str
    victim_fingerprints: set[str] = field(default_factory=set)

    @property
    def victim_count(self) -> int:
        return len(self.victim_fingerprints)

    @property
    def magnitude(self) -> str:
        n = self.victim_count
        if n >= 100:
            return "critical"
        if n >= 10:
            return "high"
        if n >= 2:
            return "medium"
        return "low"


class VictimTracker:
    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}

    def record(self, event: BeaconEvent) -> Incident:
        # Only foreign-origin (clone) events create victim incidents.
        if not event.is_foreign_origin:
            raise ValueError("victim tracking applies to foreign-origin events only")
        key = f"{event.cluster or event.origin}"
        inc = self._incidents.get(key)
        if inc is None:
            inc = Incident(cluster=event.cluster or "uncategorized", origin=event.origin)
            self._incidents[key] = inc
        inc.victim_fingerprints.add(event.fingerprint)
        return inc

    def incidents(self) -> list[Incident]:
        return sorted(self._incidents.values(), key=lambda i: i.victim_count, reverse=True)
