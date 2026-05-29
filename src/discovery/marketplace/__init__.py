"""v07 W3 — Marketplace / counterfeit & rogue-seller detection.

Net-new surface (Bolster/Fortra anti-counterfeiting parity). Scans marketplaces
(Amazon, eBay, Etsy, AliExpress, Shopify storefronts) for counterfeit listings
of a brand, scoring counterfeit-language (listing_nlp) and price anomalies
(too-cheap-to-be-real). Feeds a `listing_nlp` signal into composite.score().
Live marketplace APIs are 🔒 BLOCKED-ENV (replay default).
"""
from __future__ import annotations

from .base import ListingFinding, MarketplaceAdapter, MARKETPLACES
from .engine import MarketplaceEngine, search_all_marketplaces
from .listing_nlp import counterfeit_language_score, CounterfeitSignals
from .price_anomaly import price_anomaly_score

__all__ = [
    "ListingFinding", "MarketplaceAdapter", "MARKETPLACES",
    "MarketplaceEngine", "search_all_marketplaces",
    "counterfeit_language_score", "CounterfeitSignals", "price_anomaly_score",
]
