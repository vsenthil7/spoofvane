"""
Mobile-app store impersonation discovery.

Phishing operators publish fake apps that impersonate the target brand:

* **Google Play** — sideloaded look-alike apps (often with names like
  "Acme Bank Mobile") that capture credentials and OTP via SMS interception
* **Apple App Store** — rarer due to App Store review, but happens on
  iOS via TestFlight invites and enterprise certs
* **Sideload landing pages** — pages like ``acme-bank-mobile-apk.com``
  hosting a malicious APK download with a brand-mimicking install card

This source runs three sub-feeds:

1. ``play_store_search(brand_name)`` via Bright Data Web Scraper API
2. ``app_store_search(brand_name)`` via Bright Data Web Scraper API
3. SERP search for ``"<brand> apk download"`` and ``"<brand> mobile app install"``
   via Bright Data SERP API, filtering for sideload-style domains

For each candidate that doesn't match the brand's official developer
identity, emit a SuspectURL. The inspection layer then renders the page
(or app's store listing) and the scoring layer compares against the brand's
canonical mobile-app metadata.

In MOCK_MODE we emit a fixed set of plausible fixtures.
"""

from __future__ import annotations

from typing import Iterator

from ..common.ids import suspect_id
from ..common.logging import get_logger
from ..common.models import Brand, Source, SuspectURL
from ..common.settings import get_settings
from .base import is_same_brand_domain

logger = get_logger(__name__)


class MobileAppStoreSource:
    """Discovery source for impersonating mobile apps and APK sideload pages."""

    name = "mobile_app_store"

    def __init__(self) -> None:
        self.settings = get_settings()

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        if self.settings.mock_mode:
            yield from self._mock_yield(brand)
            return
        logger.warning(
            "mobile_app_store.live_mode_not_implemented",
            note="Set MOCK_MODE=true for fixture data",
        )
        return

    def _mock_yield(self, brand: Brand) -> Iterator[SuspectURL]:
        slug = brand.name.lower().replace(" ", "-")
        # 1. APK sideload pages
        sideload_urls = [
            f"https://{slug}-mobile-apk.com/download",
            f"https://download-{slug}-app.io/android",
            f"https://www.{slug}.com/mobile",  # the brand's real site — should be filtered
        ]
        for url in sideload_urls:
            if is_same_brand_domain(url, brand):
                continue
            yield SuspectURL(
                id=suspect_id(),
                brand_id=brand.id,
                url=url,
                source=Source.MOBILE_APP_STORE,
                discovery_metadata={
                    "channel": "apk_sideload",
                    "query": f'"{brand.name}" apk download',
                    "warning": "Direct APK install bypasses Play Store review",
                },
            )

        # 2. Play Store look-alikes — published as URLs not enforced by
        # is_same_brand_domain (play.google.com itself is benign; the
        # *listing* on Play is what's impersonating)
        playstore_listings = [
            (
                f"https://play.google.com/store/apps/details?id=com.fake.{slug}mobile",
                f"{brand.name} Mobile",
                "Genericware Ltd",  # fake developer name
            ),
            (
                f"https://play.google.com/store/apps/details?id=com.scammer.{slug}wallet",
                f"{brand.name} Wallet",
                "Suspicious Dev",
            ),
        ]
        for url, app_name, developer in playstore_listings:
            yield SuspectURL(
                id=suspect_id(),
                brand_id=brand.id,
                url=url,
                source=Source.MOBILE_APP_STORE,
                discovery_metadata={
                    "channel": "play_store",
                    "app_name": app_name,
                    "developer": developer,
                    "warning": f"Developer '{developer}' is not verified for {brand.name}",
                },
            )

        # 3. App Store look-alikes (rarer but happen)
        yield SuspectURL(
            id=suspect_id(),
            brand_id=brand.id,
            url=f"https://apps.apple.com/us/app/{slug}-mobile/id9876543210",
            source=Source.MOBILE_APP_STORE,
            discovery_metadata={
                "channel": "app_store",
                "app_name": f"{brand.name} Mobile",
                "developer": "Unverified Dev",
            },
        )
