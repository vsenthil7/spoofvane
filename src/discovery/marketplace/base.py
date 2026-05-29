"""W3 marketplace base: ListingFinding + adapter with live/replay/mock."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from .listing_nlp import counterfeit_language_score
from .price_anomaly import price_anomaly_score

MARKETPLACES = (
    "amazon", "ebay", "etsy", "aliexpress", "shopify_storefronts", "walmart",
)


@dataclass
class ListingFinding:
    marketplace: str
    seller: str
    title: str
    description: str
    price: float
    msrp: float
    images: list[str]
    url: str
    counterfeit_language: float = 0.0
    price_anomaly: float = 0.0
    authorized: bool = False

    @property
    def listing_nlp_signal(self) -> float:
        """Combined signal fed into composite.score() as `listing_nlp`."""
        if self.authorized:
            return round(min(self.counterfeit_language, 0.2), 4)
        return round(min(1.0, 0.6 * self.counterfeit_language + 0.4 * self.price_anomaly), 4)


# Two canonical listing archetypes the replay lane emits, so the differential
# probe sees materially different inputs.
_COUNTERFEIT_TITLE = "Genuine OEM replica - 1:1 super clone, AAA quality, no box"
_AUTHORIZED_TITLE = "Official store - authorized reseller with manufacturer warranty"


class MarketplaceAdapter:
    def __init__(self, marketplace: str) -> None:
        if marketplace not in MARKETPLACES:
            raise ValueError(f"unknown marketplace {marketplace}")
        self.marketplace = marketplace

    def _mode(self) -> str:
        return os.getenv("SPOOFVANE_BD_MODE", "replay").lower()

    def search(self, brand_name: str, msrp: float = 100.0) -> list[ListingFinding]:
        if self._mode() == "live":  # pragma: no cover - BLOCKED-ENV
            raise NotImplementedError(
                f"live {self.marketplace} search needs marketplace APIs (BLOCKED-ENV)")
        return self._replay(brand_name, msrp)

    def _replay(self, brand_name: str, msrp: float) -> list[ListingFinding]:
        base = int(hashlib.sha256(f"{self.marketplace}|{brand_name}".encode()).hexdigest()[:8], 16)
        n = base % 3
        out: list[ListingFinding] = []
        for i in range(n):
            s = int(hashlib.sha256(f"{self.marketplace}|{brand_name}|{i}".encode()).hexdigest()[:8], 16)
            is_counterfeit = (s % 2 == 0)
            if is_counterfeit:
                title = f"{brand_name} {_COUNTERFEIT_TITLE}"
                price = round(msrp * (0.05 + (s % 20) / 100), 2)  # 5-25% of MSRP
                authorized = False
            else:
                title = f"{brand_name} {_AUTHORIZED_TITLE}"
                price = round(msrp * (0.9 + (s % 15) / 100), 2)  # near MSRP
                authorized = True
            cf = counterfeit_language_score(title)
            pa = price_anomaly_score(price, msrp)
            out.append(ListingFinding(
                marketplace=self.marketplace,
                seller=f"seller_{s % 9999}",
                title=title, description="",
                price=price, msrp=msrp,
                images=[f"https://img-{s % 999}.example/{brand_name.lower()}.jpg"],
                url=f"https://{self.marketplace}.example/itm/{s % 999999}",
                counterfeit_language=cf.score,
                price_anomaly=pa,
                authorized=authorized,
            ))
        return out
