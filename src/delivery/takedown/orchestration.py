"""v07 W6 — Takedown orchestration network (the #1 competitive differentiator).

ZeroFox (1M/yr, 80+ partners), Bolster (unlimited), Doppel (8x faster). Today
only cloudflare/godaddy/namecheap/hosting_abuse providers exist. This adds the
ORCHESTRATION layer on top:

* takedown_router  — selects the right channel(s) by IoC type
                     (domain -> registrar+host+safebrowsing; social -> platform;
                      app -> store).
* escalation_ladder — auto -> analyst -> legal escalation model.
* takedown_sla     — time-to-takedown tracking across state transitions.

No real submission runs without an audited, RBAC-gated, human-confirmed path;
live submissions are 🔒 BLOCKED-ENV (replay/mock).
"""
from __future__ import annotations

from .takedown_router import route_takedown, TakedownCase, IocType, Channel
from .escalation_ladder import EscalationLadder, EscalationTier
from .takedown_sla import SlaTracker, SlaState

__all__ = [
    "route_takedown", "TakedownCase", "IocType", "Channel",
    "EscalationLadder", "EscalationTier", "SlaTracker", "SlaState",
]
