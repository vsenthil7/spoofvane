"""W4 actor tracker: builds recurring-actor profiles from intel hits.

Aggregates hits by actor handle into profiles (channels seen, total hits, first/
last seen, brands targeted) that feed the W12 threat-actor graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import IntelHit


@dataclass
class ActorProfile:
    actor: str
    hit_count: int
    channels: list[str]
    brands_targeted: list[str]
    first_seen: str
    last_seen: str
    max_risk: float


class ActorTracker:
    def build_profiles(self, hits: list[IntelHit]) -> list[ActorProfile]:
        by_actor: dict[str, list[IntelHit]] = {}
        for h in hits:
            if h.actor:
                by_actor.setdefault(h.actor, []).append(h)
        profiles: list[ActorProfile] = []
        for actor, ahits in by_actor.items():
            seens = sorted(h.first_seen for h in ahits)
            brands: set[str] = set()
            for h in ahits:
                brands.update(h.matched_terms)
            profiles.append(ActorProfile(
                actor=actor,
                hit_count=len(ahits),
                channels=sorted({h.channel for h in ahits}),
                brands_targeted=sorted(brands),
                first_seen=seens[0],
                last_seen=seens[-1],
                max_risk=round(max(h.risk for h in ahits), 4),
            ))
        profiles.sort(key=lambda p: (p.hit_count, p.max_risk), reverse=True)
        return profiles
