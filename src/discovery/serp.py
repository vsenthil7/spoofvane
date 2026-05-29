"""SERP API discovery source.

For each brand we run a rolling set of brand-targeted phishing queries
against Google via the Bright Data SERP API. Any organic result whose
host is *not* the brand's canonical domain becomes a suspect URL.

In MOCK_MODE this returns fixture data so the dashboard can demo
without network access.
"""
from __future__ import annotations

from typing import Iterator

import httpx

from ..common.ids import suspect_id
from ..common.logging import get_logger
from ..common.models import Brand, Source, SuspectURL
from ..common.settings import get_settings
from .base import DiscoverySource, is_same_brand_domain

log = get_logger(__name__)


_DEFAULT_QUERY_TEMPLATES = [
    '"{brand}" login',
    '"{brand}" account verify',
    '"{brand}" secure sign in',
    '"{brand}" password reset',
    '"{brand}" customer support',
    '"{brand}" online banking',
]


class SERPSource:
    """Bright Data SERP API discovery source."""

    name = "serp"

    def __init__(self, query_templates: list[str] | None = None) -> None:
        self.query_templates = query_templates or _DEFAULT_QUERY_TEMPLATES

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        settings = get_settings()
        queries = self._build_queries(brand)

        for query in queries:
            try:
                hits = self._run_query(query, brand.target_country)
            except Exception as exc:  # noqa: BLE001
                log.warning("serp_query_failed", brand=brand.name, query=query, error=str(exc))
                continue

            log.info("serp_query_done", brand=brand.name, query=query, hits=len(hits))

            for hit_url in hits:
                if is_same_brand_domain(hit_url, brand):
                    continue
                yield SuspectURL(
                    id=suspect_id(),
                    brand_id=brand.id,
                    url=hit_url,
                    source=Source.SERP,
                    discovery_metadata={"query": query, "country": brand.target_country},
                )

    # ─── internals ──────────────────────────────────────────────────────

    def _build_queries(self, brand: Brand) -> list[str]:
        primary = brand.brand_keywords[0] if brand.brand_keywords else brand.name
        return [tmpl.format(brand=primary) for tmpl in self.query_templates]

    def _run_query(self, query: str, country: str) -> list[str]:
        settings = get_settings()
        if settings.mock_mode:
            return self._mock_hits(query)

        # Live mode — Bright Data SERP API.
        # The SERP API is accessed as an HTTP proxy returning Google's HTML/JSON.
        proxy_url = f"http://brd-customer-{settings.brightdata_proxy_user}:{settings.brightdata_proxy_pass}@{settings.brightdata_serp_host}"
        target_url = f"https://www.google.com/search?q={query}&gl={country.lower()}&num=20&brd_json=1"

        with httpx.Client(proxies=proxy_url, timeout=30.0, verify=False) as client:
            resp = client.get(target_url)
            resp.raise_for_status()
            data = resp.json()

        organic = data.get("organic", [])
        return [item["link"] for item in organic if "link" in item][:20]

    @staticmethod
    def _mock_hits(query: str) -> list[str]:
        """Return plausible fixture hits for demo.

        Includes a benign result, a typosquat, and an unrelated-looking
        phishing domain so the downstream pipeline has interesting work.
        """
        # The exact URLs don't have to resolve; the demo fixture inspector
        # returns canned screenshots for them.
        base_slug = query.lower().split('"')[1] if '"' in query else "brand"
        slug = base_slug.replace(" ", "-")
        return [
            f"https://www.{slug.split('-')[0]}.com/help",  # benign
            f"https://{slug}-secure-login.com/",  # typosquat-style
            f"https://account-update-portal.xyz/{slug}",  # unrelated domain, the dangerous one
            f"https://my-{slug}-support.net/auth",  # plausible-look
            f"https://help.{slug.split('-')[0]}.org/contact",  # benign
        ]
