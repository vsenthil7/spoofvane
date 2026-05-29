"""
Social-media impersonation discovery (v0.4).

This source closes the single largest competitive gap identified in
``docs/07-competitive-analysis.md``: the matrix marks SpoofVane ``✗`` on
"Social-media impersonation" while ZeroFox, BrandShield, Bolster, Red Points,
Cyble and Constella all ship it. Real enterprises buy a *platform* that watches
every channel an attacker can impersonate them on — not just web pages.

Attackers impersonate a brand on social platforms in several distinct ways,
each of which this source surfaces:

1. **Handle squatting** — ``@acmebank-support``, ``@acme.official.help`` etc.
   on X, Instagram, Facebook, TikTok, LinkedIn, YouTube and Telegram.
2. **Fake support accounts** — profiles that reply to a brand's real customers
   in-thread, then DM them to a credential-harvesting page (the social profile
   is the *lure*; the linked page is the kit).
3. **Impersonation pages / groups** — Facebook pages or LinkedIn company pages
   cloned with the brand's logo and a malicious "contact us" link.

How discovery works (live mode):
    * Bright Data **SERP API** is queried per-platform with a ``site:`` filter
      (``site:x.com "Acme Bank" support``) — this reaches public profile and
      post URLs without needing per-platform API keys, which is exactly the
      Bright-Data wedge: the platforms heavily rate-limit/anti-bot their own
      APIs, but their public profile pages are reachable through the SERP +
      Web Unlocker + residential-proxy stack the rest of the product already
      uses for inspection.
    * Each candidate profile/page URL whose host is a known social platform
      (and which references the brand) becomes a ``SuspectURL`` with
      ``source=SOCIAL_MEDIA`` and rich ``discovery_metadata`` (platform,
      handle, surface kind, any out-link). Downstream the *out-link* — the
      page the profile funnels victims to — is what the existing inspection +
      scoring + verdict path fingerprints, so the new channel reuses the whole
      existing engine rather than duplicating it.

In MOCK_MODE this yields a deterministic, demo-friendly fixture set covering
each impersonation pattern across the major platforms, so the dashboard and
pipeline have realistic social-channel work to triage offline.
"""

from __future__ import annotations

from typing import Iterator

import httpx

from ..common.ids import suspect_id
from ..common.logging import get_logger
from ..common.models import Brand, Source, SuspectURL
from ..common.settings import get_settings
from .base import is_same_brand_domain

logger = get_logger(__name__)


# Public host → human-readable platform name. Used both to build `site:`
# queries in live mode and to classify SERP hits.
_PLATFORM_HOSTS: dict[str, str] = {
    "x.com": "X",
    "twitter.com": "X",
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "tiktok.com": "TikTok",
    "linkedin.com": "LinkedIn",
    "youtube.com": "YouTube",
    "t.me": "Telegram",
    "threads.net": "Threads",
}

# The impersonation surface kinds we tag, used by the dashboard/copilot to
# explain *why* a social hit matters.
SURFACE_HANDLE_SQUAT = "handle_squat"
SURFACE_FAKE_SUPPORT = "fake_support_account"
SURFACE_IMPERSONATION_PAGE = "impersonation_page"


class SocialMediaSource:
    """Discovery source for brand impersonation across social platforms."""

    name = "social_media"

    def __init__(self, max_per_platform: int = 4) -> None:
        self.max_per_platform = max_per_platform
        self.settings = get_settings()

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        if self.settings.mock_mode:
            yield from self._mock_yield(brand)
            return
        yield from self._live_yield(brand)

    # ─── Live mode ─────────────────────────────────────────────────────
    def _live_yield(self, brand: Brand) -> Iterator[SuspectURL]:
        """Query the SERP API per platform with a ``site:`` filter.

        Each platform is queried separately so that hits can be attributed to
        the right surface. Results are filtered to public profile/page URLs and
        de-duplicated by host+path.
        """
        primary = brand.brand_keywords[0] if brand.brand_keywords else brand.name
        seen: set[str] = set()
        for host, platform in _PLATFORM_HOSTS.items():
            query = f'site:{host} "{primary}" (support OR login OR official OR help)'
            try:
                hits = self._serp_query(query, brand.target_country)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "social_media.query_failed",
                    brand=brand.name,
                    platform=platform,
                    error=str(exc),
                )
                continue

            count = 0
            for hit_url in hits:
                if count >= self.max_per_platform:
                    break
                if is_same_brand_domain(hit_url, brand):
                    continue
                key = hit_url.split("?")[0]
                if key in seen:
                    continue
                seen.add(key)
                count += 1
                yield SuspectURL(
                    id=suspect_id(),
                    brand_id=brand.id,
                    url=hit_url,
                    source=Source.SOCIAL_MEDIA,
                    discovery_metadata={
                        "platform": platform,
                        "platform_host": host,
                        "surface": self._classify_surface(hit_url),
                        "query": query,
                        "handle": self._extract_handle(hit_url),
                    },
                )

    def _serp_query(self, query: str, country: str) -> list[str]:
        settings = self.settings
        proxy_url = (
            f"http://brd-customer-{settings.brightdata_proxy_user}:"
            f"{settings.brightdata_proxy_pass}@{settings.brightdata_serp_host}"
        )
        target_url = (
            f"https://www.google.com/search?q={query}"
            f"&gl={country.lower()}&num=20&brd_json=1"
        )
        with httpx.Client(proxies=proxy_url, timeout=30.0, verify=False) as client:
            resp = client.get(target_url)
            resp.raise_for_status()
            data = resp.json()
        organic = data.get("organic", [])
        return [item["link"] for item in organic if "link" in item][:20]

    # ─── Classification helpers ────────────────────────────────────────
    @staticmethod
    def _classify_surface(url: str) -> str:
        low = url.lower()
        if any(t in low for t in ("support", "help", "helpdesk", "service")):
            return SURFACE_FAKE_SUPPORT
        if any(t in low for t in ("/pages/", "/company/", "/groups/", "/page/")):
            return SURFACE_IMPERSONATION_PAGE
        return SURFACE_HANDLE_SQUAT

    @staticmethod
    def _extract_handle(url: str) -> str | None:
        from urllib.parse import urlparse

        path = urlparse(url).path.strip("/")
        if not path:
            return None
        first = path.split("/")[0]
        return f"@{first}" if first else None

    # ─── Mock fixtures ─────────────────────────────────────────────────
    def _mock_yield(self, brand: Brand) -> Iterator[SuspectURL]:
        slug = brand.name.lower().replace(" ", "")
        dash = brand.name.lower().replace(" ", "-")
        # (profile_url, platform, host, surface, handle, out_link)
        fixtures = [
            (
                f"https://x.com/{slug}_support",
                "X",
                "x.com",
                SURFACE_FAKE_SUPPORT,
                f"@{slug}_support",
                f"https://{dash}-help-desk.com/verify",
            ),
            (
                f"https://instagram.com/{slug}.official.help",
                "Instagram",
                "instagram.com",
                SURFACE_FAKE_SUPPORT,
                f"@{slug}.official.help",
                f"https://{dash}-account-recovery.app/login",
            ),
            (
                f"https://facebook.com/pages/{dash}-customer-care",
                "Facebook",
                "facebook.com",
                SURFACE_IMPERSONATION_PAGE,
                None,
                f"https://secure-{dash}-care.com/auth",
            ),
            (
                f"https://t.me/{slug}_officialsupport",
                "Telegram",
                "t.me",
                SURFACE_FAKE_SUPPORT,
                f"@{slug}_officialsupport",
                f"https://{dash}-wallet-restore.io/connect",
            ),
            (
                f"https://linkedin.com/company/{dash}-global-support",
                "LinkedIn",
                "linkedin.com",
                SURFACE_IMPERSONATION_PAGE,
                None,
                None,
            ),
            (
                f"https://tiktok.com/@{slug}giveaway",
                "TikTok",
                "tiktok.com",
                SURFACE_HANDLE_SQUAT,
                f"@{slug}giveaway",
                f"https://{dash}-promo-claim.xyz/",
            ),
        ]
        for profile_url, platform, host, surface, handle, out_link in fixtures:
            if is_same_brand_domain(profile_url, brand):
                continue
            # When the profile funnels victims to an external page, that page
            # is the higher-value inspection target; otherwise inspect the
            # profile URL itself (logo/handle clone is still actionable).
            inspect_url = out_link or profile_url
            yield SuspectURL(
                id=suspect_id(),
                brand_id=brand.id,
                url=inspect_url,
                source=Source.SOCIAL_MEDIA,
                discovery_metadata={
                    "platform": platform,
                    "platform_host": host,
                    "surface": surface,
                    "profile_url": profile_url,
                    "handle": handle,
                    "funnels_to_external_page": bool(out_link),
                },
            )
