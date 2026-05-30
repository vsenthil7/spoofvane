"""v07 W4 — Dark-web & underground intelligence (net-new package).

Competitors (ZeroFox, Recorded Future, Flare, Constella) treat this as core.
Monitors tor forums, telegram channels, paste sites, breach dumps, and combo
lists for brand/exec/domain mentions, with deduplication + freshness
verification (Constella pattern). Builds recurring-actor profiles feeding the
W12 graph. Live Tor/Telegram collection is 🔒 BLOCKED-ENV; replay ships curated
SYNTHETIC fixtures only — never real PII or real dark-web content.
"""
from __future__ import annotations

from .base import IntelHit, DarkWebSource, SOURCES
from .keyword_matcher import KeywordMatcher, match_keywords
from .actor_tracker import ActorTracker, ActorProfile

__all__ = [
    "IntelHit", "DarkWebSource", "SOURCES",
    "KeywordMatcher", "match_keywords",
    "ActorTracker", "ActorProfile",
]
