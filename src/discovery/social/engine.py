"""W1 social engine — runs all platform adapters and aggregates findings."""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import SocialAdapter, SocialFinding, PLATFORMS


@dataclass
class SocialEngine:
    platforms: tuple[str, ...] = PLATFORMS

    def search(self, brand_name: str, brand_handle: str, brand_logo_hash: str) -> list[SocialFinding]:
        out: list[SocialFinding] = []
        for p in self.platforms:
            out.extend(SocialAdapter(p).search(brand_name, brand_handle, brand_logo_hash))
        # Highest-risk impersonators first.
        out.sort(key=lambda f: f.social_clone_signal, reverse=True)
        return out


def search_all_platforms(brand_name: str, brand_handle: str, brand_logo_hash: str) -> list[SocialFinding]:
    return SocialEngine().search(brand_name, brand_handle, brand_logo_hash)
