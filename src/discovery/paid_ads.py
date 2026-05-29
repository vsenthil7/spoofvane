"""
Paid-search / SERP-ad abuse discovery.

Phishing operators frequently buy paid ads on brand keywords to outrank the
legitimate site. A user searching for "acme bank login" sees a sponsored ad
for "Acme Bank Official Login" pointing at ``acme-bank-portal[.]xyz``. The
ad copy reads as legitimate; the destination is the phishing kit.

This source asks Bright Data's SERP API specifically for the *ads* slot on
brand-keyword queries, normalises the destination URLs, filters out the
brand's own domain, and emits each remaining URL as a SuspectURL with a
``source=SERP_ADS`` flag.

Detecting this matters because:

1. Paid-ad placement is *fast* — operators can rotate ad creative within
   hours of a takedown, so manual monitoring is impractical.
2. Many primary brand-protection vendors focus on organic SERP and miss
   the sponsored slots entirely.
3. The destination URL is often a single-page funnel that doesn't appear
   in cert-transparency or zone deltas.

In MOCK_MODE this source yields a small fixed set of plausible fixtures so
the demo pipeline has work to do.
"""

from __future__ import annotations

from typing import Iterator

from ..common.ids import suspect_id
from ..common.logging import get_logger
from ..common.models import Brand, Source, SuspectURL
from ..common.settings import get_settings
from .base import is_same_brand_domain

logger = get_logger(__name__)


class PaidAdSource:
    """Discovery source for sponsored / paid-ad SERP slots."""

    name = "paid_ads"

    def __init__(self, max_per_query: int = 5) -> None:
        self.max_per_query = max_per_query
        self.settings = get_settings()

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        if self.settings.mock_mode:
            yield from self._mock_yield(brand)
            return
        # Live mode: use Bright Data SERP API with adsOnly=true (sketch).
        # Real implementation would call the SERP endpoint with
        # google_search?engines=ads and parse the structured `paid_results`
        # field. Left as a hook to avoid network in this prototype.
        logger.warning(
            "paid_ads.live_mode_not_implemented",
            note="Set MOCK_MODE=true for fixture data",
        )
        return

    # ─── Mock fixtures ─────────────────────────────────────────────────
    def _mock_yield(self, brand: Brand) -> Iterator[SuspectURL]:
        slug = brand.name.lower().replace(" ", "-")
        fixtures = [
            (
                f"https://{slug}-official-login.com/",
                "Sign in to your account – Official",
                f"{slug}-official-login.com",
            ),
            (
                f"https://login-{slug}-portal.app/",
                f"{brand.name} Online Banking Portal",
                f"login-{slug}-portal.app",
            ),
            (
                f"https://secure-{slug}-access.io/auth",
                f"Verify {brand.name} account — official site",
                f"secure-{slug}-access.io",
            ),
            (
                f"https://www.{slug}.com/",  # the real one — should be filtered
                brand.name,
                f"www.{slug}.com",
            ),
        ]
        for url, ad_title, ad_display_url in fixtures[: self.max_per_query]:
            if is_same_brand_domain(url, brand):
                logger.debug("paid_ads.skipped_canonical", url=url)
                continue
            yield SuspectURL(
                id=suspect_id(),
                brand_id=brand.id,
                url=url,
                source=Source.PAID_AD,
                discovery_metadata={
                    "ad_title": ad_title,
                    "ad_display_url": ad_display_url,
                    "query": f'"{brand.name}" login',
                    "slot": "top_ads",
                },
            )
