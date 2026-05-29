"""Inspect a suspect URL.

The real inspector drives Bright Data's Scraping Browser via the Chrome
DevTools Protocol over WebSocket. It uses Web Unlocker (engaged automatically
by Bright Data when a JS challenge is detected) and a residential proxy
pinned to the brand's ``target_country``.

The mock inspector returns canned screenshots so the demo runs without a
network or an account.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

from ..common.ids import inspection_id
from ..common.logging import get_logger
from ..common.models import Brand, InspectionResult, SuspectURL
from ..common.settings import get_settings
from ..storage.blob_store import write_blob

log = get_logger(__name__)


class Inspector(Protocol):
    def inspect(self, brand: Brand, suspect: SuspectURL) -> InspectionResult: ...


# ─── Bright Data inspector (live mode) ─────────────────────────────────


class BrightDataInspector:
    """Drive the Bright Data Scraping Browser over CDP.

    NB: in this hackathon prototype the live implementation is sketched
    (it depends on ``playwright`` and a CDP connection to Bright Data).
    The structure is real and the entrypoints are testable; the actual
    network round-trip is not exercised in the bundled tests.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def inspect(self, brand: Brand, suspect: SuspectURL) -> InspectionResult:
        try:
            # Playwright is heavy and optional; only import here.
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            return self._failure(
                suspect,
                "playwright not installed; install playwright + browsers for live mode",
            )

        log.info("inspect_live", url=suspect.url, country=brand.target_country)
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(
                    f"{self.settings.brightdata_cdp_endpoint}?country={brand.target_country.lower()}"
                )
                context = browser.new_context()
                page = context.new_page()
                resp = page.goto(suspect.url, wait_until="networkidle", timeout=45_000)
                final_url = page.url
                http_status = resp.status if resp else None

                screenshot_bytes = page.screenshot(full_page=True)
                dom = page.content().encode("utf-8")

                # Best-effort favicon fetch
                favicon_bytes = self._fetch_favicon(page, suspect.url)

                browser.close()
        except Exception as exc:  # noqa: BLE001
            log.error("inspect_failed", url=suspect.url, error=str(exc))
            return self._failure(suspect, str(exc))

        screenshot_hash, screenshot_path = write_blob(screenshot_bytes, suffix=".png")
        dom_hash, dom_path = write_blob(dom, suffix=".html")
        favicon_hash = hashlib.md5(favicon_bytes).hexdigest() if favicon_bytes else None

        return InspectionResult(
            id=inspection_id(),
            suspect_url_id=suspect.id,
            success=True,
            rendered_country=brand.target_country,
            final_url=final_url,
            http_status=http_status,
            screenshot_path=screenshot_path,
            screenshot_hash=screenshot_hash,
            dom_path=dom_path,
            dom_hash=dom_hash,
            favicon_hash=favicon_hash,
            js_bundle_hashes=[],
            asn=None,
            registrar=None,
            registration_date=None,
        )

    @staticmethod
    def _fetch_favicon(page, url: str) -> bytes:
        from urllib.parse import urljoin

        try:
            href = page.eval_on_selector(
                "link[rel*='icon']", "el => el.href"
            )
        except Exception:
            href = None
        favicon_url = href or urljoin(url, "/favicon.ico")
        try:
            resp = page.request.get(favicon_url, timeout=10_000)
            if resp.ok:
                return resp.body()
        except Exception:
            pass
        return b""

    def _failure(self, suspect: SuspectURL, error: str) -> InspectionResult:
        return InspectionResult(
            id=inspection_id(),
            suspect_url_id=suspect.id,
            success=False,
            rendered_country=self.settings.brightdata_proxy_user[:2] if self.settings.brightdata_proxy_user else "US",
            error=error,
        )


# ─── Mock inspector (MOCK_MODE) ────────────────────────────────────────


_PHISH_HOST_HINTS = (
    # Generic typosquats
    "account-update-portal", "secure-login", "verify-account", "auth",
    "portal", "support.net",
    # Banking family
    "-bank-", "deposit",
    # Microsoft / M365 family
    "outlook-", "-365",
    # Crypto family
    "wallet-", "metamask",
    # Payment family
    "checkout-", "billing",
    # Tech-support scam family
    "techsupport",
    # Kit family signatures
    "tycoon-", "evilproxy", "caffeine-", "16shop",
    # Geo-cloaked fixtures
    "geo-",
)
_BENIGN_HOST_HINTS = ("help.", "contact", "/help", ".org")


class MockInspector:
    """Deterministic fixture inspector.

    Generates a synthetic but realistic screenshot for each URL based on
    string heuristics so the downstream similarity scorer has interesting
    inputs.
    """

    def inspect(self, brand: Brand, suspect: SuspectURL) -> InspectionResult:
        host = (urlparse(suspect.url).hostname or "").lower()
        path = (urlparse(suspect.url).path or "").lower()
        is_phishy = any(h in host or h in path for h in _PHISH_HOST_HINTS)
        is_benign = any(h in host or h in path for h in _BENIGN_HOST_HINTS) and not is_phishy

        # The brand's own canonical login URL is always rendered as a login
        # page (i.e., phishy template) so the similarity baseline is "real
        # login page" — not the help-center fallback. Without this, the
        # canonical baseline is benign and every other benign result scores
        # 1.0 against it, producing false positives.
        is_canonical_baseline = (
            suspect.discovery_metadata.get("role") == "canonical_baseline"
        )
        if is_canonical_baseline:
            is_phishy = True
            is_benign = False

        # Time-bomb simulation. A URL carrying "timebomb" in its host or a
        # time_bomb flag renders as a benign holding page on first inspection
        # (recheck_count 0), then flips to a phishing payload on re-inspection
        # (recheck_count >= 1). This exercises the diff-detector: a previously-
        # benign URL that now looks like a login page is a high-confidence
        # activation signal.
        recheck_count = int(suspect.discovery_metadata.get("recheck_count", 0))
        url_says_timebomb = "timebomb" in host or "timebomb" in path
        flag_says_timebomb = "timebomb" in suspect.discovery_metadata.get("flags", [])
        if (url_says_timebomb or flag_says_timebomb):
            if recheck_count >= 1:
                is_phishy, is_benign = True, False  # activated
            else:
                is_phishy, is_benign = False, True   # still dormant

        # Geo-cloaking simulation. URLs whose host contains "geo-" or that
        # carry an explicit "cloak" flag in their discovery metadata only
        # serve the phishing payload from their "primary" region (derived
        # from the URL hash); from any other region we render a benign
        # holding page. This is what real geo-targeted phishing kits do,
        # and is the signal multi-region inspection is designed to surface.
        rendered_country = brand.target_country
        url_says_cloaked = "geo-" in host or "geo-" in path
        flag_says_cloaked = "cloak" in suspect.discovery_metadata.get("flags", [])
        cloak_eligible = url_says_cloaked or flag_says_cloaked

        if cloak_eligible:
            # When cloaking is in play we *force* phishy behaviour from the
            # primary region (so the cloak has something to cloak), and
            # benign from every other region.
            if self._is_primary_region_for_url(suspect.url, rendered_country):
                effective_phishy, effective_benign = True, False
            else:
                effective_phishy, effective_benign = False, True
        else:
            effective_phishy, effective_benign = is_phishy, is_benign

        # Build the synthetic screenshot
        screenshot = self._render_synthetic(
            brand, suspect.url, is_phishy=effective_phishy, is_benign=effective_benign
        )
        buf = BytesIO()
        screenshot.save(buf, format="PNG")
        screenshot_bytes = buf.getvalue()

        dom = self._render_dom(brand, suspect.url, is_phishy=effective_phishy).encode("utf-8")

        favicon_bytes = self._render_favicon(brand, mimic=is_phishy)

        screenshot_hash, screenshot_path = write_blob(screenshot_bytes, suffix=".png")
        dom_hash, dom_path = write_blob(dom, suffix=".html")
        favicon_hash = hashlib.md5(favicon_bytes).hexdigest()

        # Synthesize plausible metadata
        registered_unix = suspect.discovery_metadata.get("registered_unix")
        registration_date = (
            _dt.datetime.fromtimestamp(int(registered_unix), tz=_dt.timezone.utc)
            if registered_unix
            else _dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(days=2 if is_phishy else 365)
        )
        registrar = suspect.discovery_metadata.get("registrar") or (
            "Namecheap" if is_phishy else "Verisign"
        )
        asn = "AS204957" if is_phishy else "AS13335"

        # JS bundle hashes — when the URL signals a specific kit, inject the
        # corresponding known-bad bundle hash so check_js_bundles() fires.
        bundle_hashes = [hashlib.sha256(f"bundle-{host}".encode()).hexdigest()[:16]]
        if "16shop" in suspect.url.lower():
            bundle_hashes.append("a3f9b21c2c8d1f73")
        elif "evilproxy" in suspect.url.lower():
            bundle_hashes.append("e72b9fc4901aa315")
        elif "caffeine" in suspect.url.lower():
            bundle_hashes.append("94d8f01b3e2c1a90")
        elif "tycoon" in suspect.url.lower():
            bundle_hashes.append("6f12e08d5c93b471")

        return InspectionResult(
            id=inspection_id(),
            suspect_url_id=suspect.id,
            success=True,
            rendered_country=brand.target_country,
            final_url=suspect.url,
            http_status=200,
            screenshot_path=screenshot_path,
            screenshot_hash=screenshot_hash,
            dom_path=dom_path,
            dom_hash=dom_hash,
            favicon_hash=favicon_hash,
            js_bundle_hashes=bundle_hashes,
            asn=asn,
            registrar=registrar,
            registration_date=registration_date,
        )

    # ─── synthetic rendering ───────────────────────────────────────────

    @staticmethod
    def _is_primary_region_for_url(url: str, region: str) -> bool:
        """Derive which region a (cloaked) URL "really" targets, from its host hash.

        Used by the multi-region cloaking simulation: any inspection NOT from
        that region gets the benign holding-page render.

        The candidate set is deliberately scoped to the same regions we
        inspect from by default — otherwise URL hashes mapping to FR/JP/AU/SG
        would never get caught, defeating the demo.
        """
        countries = ("US", "GB", "DE", "BR", "IN")
        h = int(hashlib.md5(url.encode()).hexdigest(), 16)
        primary = countries[h % len(countries)]
        return region.upper() == primary

    @staticmethod
    def _render_synthetic(brand: Brand, url: str, is_phishy: bool, is_benign: bool) -> Image.Image:
        """Build a 800×600 fake login-page screenshot.

        Phishy pages mimic the canonical brand login layout (so pHash + DOM
        scores light up). Benign pages diverge structurally.
        """
        W, H = 800, 600
        bg = (245, 247, 250) if not is_benign else (255, 255, 255)
        img = Image.new("RGB", (W, H), color=bg)
        draw = ImageDraw.Draw(img)

        # header bar — same colour as the brand canonical
        brand_colour = (16, 78, 139) if not is_benign else (90, 90, 90)
        draw.rectangle([0, 0, W, 70], fill=brand_colour)

        # logo placeholder
        draw.rectangle([24, 18, 180, 52], outline=(255, 255, 255), width=2)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((36, 26), brand.name[:18], fill=(255, 255, 255), font=font)

        if is_phishy or not is_benign:
            # Centred login form
            draw.rectangle([200, 160, 600, 480], outline=(200, 205, 215), width=2, fill=(255, 255, 255))
            draw.text((320, 180), "Sign in", fill=(20, 30, 50), font=font)
            draw.rectangle([240, 240, 560, 280], outline=(180, 185, 195), width=1)
            draw.text((252, 250), "email", fill=(140, 145, 155), font=font)
            draw.rectangle([240, 310, 560, 350], outline=(180, 185, 195), width=1)
            draw.text((252, 320), "password", fill=(140, 145, 155), font=font)
            draw.rectangle([240, 390, 560, 430], fill=brand_colour)
            draw.text((360, 400), "Sign in", fill=(255, 255, 255), font=font)
            if is_phishy:
                draw.text((220, 540), f"URL: {url[:70]}", fill=(255, 0, 0), font=font)
        else:
            draw.text((220, 200), "How can we help you?", fill=(30, 30, 30), font=font)
            draw.text((220, 260), "Search articles, contact support, FAQs.", fill=(80, 80, 80), font=font)

        return img

    @staticmethod
    def _render_dom(brand: Brand, url: str, is_phishy: bool) -> str:
        if not is_phishy:
            return (
                f"<html><head><title>Help center</title></head>"
                f"<body><h1>Help center</h1><p>Search articles or contact us.</p></body></html>"
            )

        # Family + kit hints from the URL/path/host. This lets the same
        # discovery feed exercise the family classifier and kit fingerprinter
        # end to end in the demo.
        url_lower = url.lower()
        family_body = ""
        kit_extras = ""

        # Family-specific content. The match has to be on a distinctive
        # family marker, not just any substring that happens to overlap with
        # the brand name. We check URL path/host segments deliberately to
        # avoid false positives.
        url_lower = url.lower()
        segments = url_lower.replace("://", "/").split("/")
        all_tokens = set()
        for seg in segments:
            for token in seg.split("-"):
                all_tokens.add(token)
                # Also split on . for hostname tokens
                for t2 in token.split("."):
                    all_tokens.add(t2)

        if {"deposit", "account"} & all_tokens and "bank" in all_tokens:
            family_body = (
                "<label>Account number</label><input name='accountnumber'>"
                "<label>Sort code</label><input name='sortcode'>"
                "<label>One time passcode (OTP)</label><input name='otp'>"
                "<p>We have detected unusual activity on your account.</p>"
            )
        elif {"outlook", "office", "microsoft", "365"} & all_tokens:
            family_body = (
                "<h1>Sign in to Microsoft 365</h1>"
                "<p>Your mailbox is full. Click here to verify your Outlook account.</p>"
                "<input name='email' placeholder='name@microsoft.com'>"
            )
        elif {"wallet", "metamask", "binance", "coinbase", "crypto"} & all_tokens:
            family_body = (
                "<h1>Connect your wallet</h1>"
                "<label>Enter your 12-word seed phrase to recover MetaMask</label>"
                "<textarea name='mnemonic'></textarea>"
                "<p>Claim your free ETH airdrop.</p>"
            )
        elif {"checkout", "billing", "pay"} & all_tokens:
            family_body = (
                "<h1>Complete payment</h1>"
                "<label>Card number</label><input name='pan'>"
                "<label>CVV</label><input name='cvv'>"
                "<label>Expiry date MM/YY</label><input name='expiry'>"
                "<p>Verified by Visa 3-D Secure check.</p>"
            )
        elif {"techsupport", "support"} & all_tokens and "help-desk" in url_lower:
            family_body = (
                "<h1>Your computer is infected!</h1>"
                "<p>Call Microsoft Support immediately: +1 800 555 1234</p>"
                "<p>A virus has been detected on your device.</p>"
            )

        # Kit hints based on URL features. Real kits leave these fingerprints
        # in the rendered DOM whether or not the brand they impersonate matches.
        if "16shop" in url_lower or "/sh16/" in url_lower:
            kit_extras = (
                "<!-- powered by 16shop -->"
                "<form class='sh16-form' action='/sh16/submit'>"
                "<input type='hidden' name='vk16' value='abc123'></form>"
            )
        elif "evilproxy" in url_lower or "ep_session" in url_lower:
            kit_extras = (
                "<script src='//cdn.epproxy.io/relay.js'></script>"
                "<input type='hidden' name='ep_session' value='xyz'>"
                "<input type='hidden' name='ep_relay' value='abc'>"
            )
        elif "tycoon" in url_lower:
            kit_extras = (
                "<!-- tycoon-2fa kit v3 -->"
                "<script src='//abc.pinata.io/aaaaaaaaaaaaaaaaaaaaaaaa'></script>"
                "<script>var t = cf_chl_gen_tk_abc;</script>"
            )
        elif "caffeine" in url_lower:
            kit_extras = (
                "<!-- powered by caffeine -->"
                "<div class='caf-modal'><form class='caf-input' action='/cf/logme'></form></div>"
            )

        return (
            f"<html><head><title>{brand.name} – Sign in</title></head>"
            f"<body><header><img src='/logo.png' alt='{brand.name}'></header>"
            f"<main>{family_body}"
            f"<form action='{url}/auth' method='post'>"
            f"<input name='email'><input name='password' type='password'>"
            f"<button type='submit'>Sign in</button></form>"
            f"{kit_extras}</main></body></html>"
        )

    @staticmethod
    def _render_favicon(brand: Brand, mimic: bool) -> bytes:
        img = Image.new("RGB", (16, 16), color=(16, 78, 139) if mimic else (200, 200, 200))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


# ─── Factory ───────────────────────────────────────────────────────────


def get_inspector() -> Inspector:
    settings = get_settings()
    if settings.mock_mode:
        log.debug("inspector_mode", mode="mock")
        return MockInspector()
    log.debug("inspector_mode", mode="live")
    return BrightDataInspector()
