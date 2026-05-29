"""Newly-registered domain discovery source.

Public TLD zone files publish a daily delta. We filter against the brand's
keyword set. In MOCK_MODE we synthesise a small fixture set.
"""
from __future__ import annotations

import time
from typing import Iterator

from ..common.ids import suspect_id
from ..common.logging import get_logger
from ..common.models import Brand, Source, SuspectURL
from ..common.settings import get_settings
from .base import is_same_brand_domain

log = get_logger(__name__)


class NewDomainsSource:
    """Daily newly-registered domain delta."""

    name = "new_domains"

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        settings = get_settings()
        for url, meta in self._stream(brand, mock=settings.mock_mode):
            if is_same_brand_domain(url, brand):
                continue
            yield SuspectURL(
                id=suspect_id(),
                brand_id=brand.id,
                url=url,
                source=Source.NEW_DOMAINS,
                discovery_metadata=meta,
            )

    def _stream(self, brand: Brand, mock: bool) -> Iterator[tuple[str, dict]]:
        if mock:
            yield from self._mock(brand)
            return

        # Live mode: query a newly-registered-domains feed.
        # Real implementations might use whoisxmlapi.com or domainsproject.org.
        log.warning("new_domains_live_not_implemented")
        return

    @staticmethod
    def _mock(brand: Brand) -> Iterator[tuple[str, dict]]:
        keyword = (brand.brand_keywords[0] if brand.brand_keywords else brand.name).lower().replace(" ", "")
        now = int(time.time())
        fixtures = [
            (f"https://{keyword}-update.app", {"registrar": "Namecheap", "registered_unix": now - 3600 * 24 * 2}),
            (f"https://my-{keyword}-login.xyz", {"registrar": "PorkBun", "registered_unix": now - 3600 * 12}),
            (f"https://{keyword}-secure-portal.net", {"registrar": "GoDaddy", "registered_unix": now - 3600 * 36}),
        ]
        yield from fixtures
