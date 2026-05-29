"""W3 marketplace engine: runs all marketplace adapters + ranks."""
from __future__ import annotations

from dataclasses import dataclass

from .base import MarketplaceAdapter, ListingFinding, MARKETPLACES


@dataclass
class MarketplaceEngine:
    marketplaces: tuple[str, ...] = MARKETPLACES

    def search(self, brand_name: str, msrp: float = 100.0) -> list[ListingFinding]:
        out: list[ListingFinding] = []
        for m in self.marketplaces:
            out.extend(MarketplaceAdapter(m).search(brand_name, msrp))
        out.sort(key=lambda f: f.listing_nlp_signal, reverse=True)
        return out


def search_all_marketplaces(brand_name: str, msrp: float = 100.0) -> list[ListingFinding]:
    return MarketplaceEngine().search(brand_name, msrp)
