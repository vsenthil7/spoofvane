"""v07 W1 — Social-impersonation engine (multi-platform).

Deepens the single discovery/social_media.py into a per-platform engine
covering the surfaces ZeroFox (180+) and Doppel emphasize. Each adapter
implements search(brand) -> list[SocialFinding] with live/replay/mock modes;
findings carry a clone_score (avatar pHash-style vs brand) and handle_risk
(homoglyph/edit-distance) that feed composite.score() as the `social_clone`
signal.
"""
from __future__ import annotations

from .base import SocialFinding, SocialAdapter, PLATFORMS
from .engine import SocialEngine, search_all_platforms

__all__ = [
    "SocialFinding", "SocialAdapter", "PLATFORMS",
    "SocialEngine", "search_all_platforms",
]
