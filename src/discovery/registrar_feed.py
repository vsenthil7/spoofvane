"""A4 — Registrar / WHOIS feed via Bright Data Datasets.

Pulls newly-registered and recently-changed domains matching brand permutations
from the Bright Data WHOIS dataset, tags each with source=brd_dataset_whois, and
queues young/suspicious domains for inspection. Uses the canonical DatasetsClient
so cost + usage are recorded automatically.
"""
from __future__ import annotations

import hashlib
from typing import Iterator

from ..common.models import Brand, Source, SuspectURL
from ..common.ids import suspect_id
from ..integrations.brightdata.clients import DatasetsClient
from .base import is_same_brand_domain

PERMUTATION_TLDS = ("com", "net", "top", "xyz", "cc", "live", "online", "support")


def _permutations(brand: Brand) -> list[str]:
    kw = (brand.brand_keywords or [brand.name.lower()])[0].replace(" ", "")
    bases = [kw, f"{kw}-login", f"{kw}-secure", f"{kw}verify", f"my-{kw}"]
    return [f"{b}.{tld}" for b in bases for tld in PERMUTATION_TLDS[:4]]


class RegistrarFeedSource:
    name = "registrar_feed"

    def __init__(self, tenant_id: str = "demo") -> None:
        self.tenant_id = tenant_id
        self.client = DatasetsClient()

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        for domain in _permutations(brand):
            rec = self.client.whois(self.tenant_id, domain)
            # Queue only young or risky registrant-country domains.
            age = rec.get("created_days_ago", 9999)
            risky_cc = rec.get("registrant_country") in ("RU", "CN", "PA", "IS")
            if age > 90 and not risky_cc:
                continue
            url = f"https://{domain}/login"
            if is_same_brand_domain(url, brand):
                continue
            yield SuspectURL(
                id=suspect_id(),
                brand_id=brand.id,
                url=url,
                source=Source.REGISTRAR_FEED,
                discovery_metadata={
                    "source_tag": rec.get("source", "brd_dataset_whois"),
                    "registrar": rec.get("registrar"),
                    "created_days_ago": age,
                    "registrant_country": rec.get("registrant_country"),
                    "is_newly_registered": age < 30,
                },
            )
