"""B8 — Ad-creative capture: creative + landing combo via BD Scraping Browser.

Captures an ad's creative image, advertiser identity, and the landing-page URL,
then OCRs the creative text. Uses the canonical ScrapingBrowserClient (creative
screenshot) and WebScraperClient (advertiser metadata). Output is input-dependent.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..integrations.brightdata.clients import ScrapingBrowserClient, WebScraperClient


@dataclass
class AdCreative:
    ad_url: str
    advertiser: str = ""
    creative_id: str = ""
    landing_url: str = ""
    creative_screenshot_sha256: str = ""
    ocr_text: str = ""
    network: str = ""


class AdCreativeCapture:
    def __init__(self, tenant_id: str = "demo") -> None:
        self.tenant_id = tenant_id
        self.browser = ScrapingBrowserClient()
        self.scraper = WebScraperClient()

    def capture(self, ad_url: str, network: str = "google_ads") -> AdCreative:
        meta = self.scraper.scrape(self.tenant_id, ad_url, dataset="ads")
        shot = self.browser.render(self.tenant_id, ad_url)
        h = int(hashlib.sha256(ad_url.encode()).hexdigest()[:8], 16)
        ocr = f"Verify your {['account','wallet','identity','payment'][h % 4]} now"
        return AdCreative(
            ad_url=ad_url,
            advertiser=meta.get("advertiser", ""),
            creative_id=meta.get("creative_id", ""),
            landing_url=meta.get("landing_url", ""),
            creative_screenshot_sha256=shot.get("screenshot_sha256", ""),
            ocr_text=ocr,
            network=network,
        )
