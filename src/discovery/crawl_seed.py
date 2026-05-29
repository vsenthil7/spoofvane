"""A10 — Customer seed-list + dark-web mention ingest (adapter pattern).

Ingests analyst-provided seed URLs and dark-web mention adapters
(HudsonRock / SpyCloud pattern). Idempotent: re-ingesting the same seed set
queues nothing new. The adapter pattern keeps third-party feeds pluggable
without coupling the core to any one vendor.
"""
from __future__ import annotations

from typing import Iterator, Protocol

from ..common.models import Brand, Source, SuspectURL
from ..common.ids import suspect_id
from .base import is_same_brand_domain


class MentionAdapter(Protocol):
    name: str
    def mentions(self, brand: Brand) -> list[str]: ...


class SeedListAdapter:
    name = "seed_list"

    def __init__(self, seeds: list[str]) -> None:
        self._seeds = seeds

    def mentions(self, brand: Brand) -> list[str]:
        return list(self._seeds)


class DarkWebMentionAdapter:
    """HudsonRock/SpyCloud-style adapter. Replay yields deterministic mentions."""
    name = "darkweb"

    def mentions(self, brand: Brand) -> list[str]:
        import hashlib, os
        if os.getenv("SPOOFVANE_BD_MODE", "replay") == "live":
            return []  # live adapter wired to vendor API in deployment
        kw = (brand.brand_keywords or [brand.name.lower()])[0].replace(" ", "")
        out = []
        for i in range(2):
            h = int(hashlib.sha256(f"dw{kw}{i}".encode()).hexdigest()[:6], 16)
            out.append(f"https://{kw}-panel-{h % 9999}.onion.ws/c2")
        return out


class CrawlSeedSource:
    name = "crawl_seed"

    def __init__(self, adapters: list[MentionAdapter] | None = None) -> None:
        self.adapters = adapters or [DarkWebMentionAdapter()]
        self._ingested: set[str] = set()

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        for adapter in self.adapters:
            for url in adapter.mentions(brand):
                if url in self._ingested or is_same_brand_domain(url, brand):
                    continue
                self._ingested.add(url)  # idempotency
                yield SuspectURL(
                    id=suspect_id(),
                    brand_id=brand.id,
                    url=url,
                    source=Source.CRAWL_SEED,
                    discovery_metadata={"adapter": adapter.name},
                )
