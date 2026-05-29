"""
Phishing-kit template fingerprinting.

Most phishing kits are mass-produced. The seller bundles a kit (16Shop,
GreatHorn, EvilProxy, Caffeine, Tycoon 2FA, etc), and dozens of operators
deploy lightly-customised clones from it. The kit leaves fingerprints:

* Specific JavaScript bundles with reused filenames or content hashes
* Specific HTML structure (form action paths, hidden input names)
* CSS class signatures the kit uses for its overlay UI
* Asset URLs pointing to the kit's CDN or pastebin droppers
* Comment strings the kit author left in the HTML

This module fingerprints rendered pages against a known-kit database. A hit
is *strong* evidence of phishing intent — far stronger than visual similarity
alone, because the brand whose login is being cloned might be irrelevant: it
matches the *kit*, not the impersonated brand.

The database here is small and illustrative. A production deployment would
ingest from sources like PhishTank kit archives, urlscan.io tag data, and
internal reverse-engineering. Updates are pushed through Bright Data Web
Scraper API workflows monitoring known kit marketplaces.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from bs4 import BeautifulSoup

from ..common.logging import get_logger
from ..common.models import InspectionResult
from ..storage.blob_store import read_blob

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class KitMatch:
    """A match against a known phishing-kit fingerprint."""

    kit_name: str
    confidence: float  # 0..1
    signatures_hit: list[str]
    notes: str

    def as_dict(self) -> dict:
        return {
            "kit_name": self.kit_name,
            "confidence": self.confidence,
            "signatures_hit": list(self.signatures_hit),
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class KitFingerprint:
    """A fingerprint definition for one known phishing kit."""

    name: str
    notes: str
    # Each is a tuple (label, pattern). All patterns are run case-insensitively.
    html_patterns: tuple[tuple[str, re.Pattern], ...] = ()
    css_classes: tuple[str, ...] = ()
    form_action_patterns: tuple[tuple[str, re.Pattern], ...] = ()
    asset_url_patterns: tuple[tuple[str, re.Pattern], ...] = ()
    hidden_input_names: tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# Known-kit database (illustrative — real production has hundreds)
# --------------------------------------------------------------------------- #


_KIT_DB: tuple[KitFingerprint, ...] = (
    KitFingerprint(
        name="16Shop",
        notes="High-volume kit-as-a-service, ~2018-present. Originally Apple ID focused.",
        html_patterns=(
            ("16shop-watermark", re.compile(r"16shop|16-shop", re.I)),
            ("apple-id-blocked", re.compile(r"your apple id has been (?:locked|blocked)", re.I)),
        ),
        css_classes=("sh16-overlay", "sh16-form"),
        form_action_patterns=(
            ("16shop-post", re.compile(r"/sh16/(?:submit|post|login)", re.I)),
        ),
        hidden_input_names=("vk16", "sh16_token"),
    ),
    KitFingerprint(
        name="EvilProxy",
        notes="Reverse-proxy AiTM kit; defeats MFA via real-time session relay.",
        html_patterns=(
            ("evilproxy-watermark", re.compile(r"evilproxy|ep_session", re.I)),
            ("proxy-redirect", re.compile(r"sessionid=[a-z0-9]{32,}.*&relay=", re.I)),
        ),
        asset_url_patterns=(
            ("evilproxy-cdn", re.compile(r"//[a-z0-9]+\.epproxy\.(?:io|com)/", re.I)),
        ),
        hidden_input_names=("ep_session", "ep_relay"),
    ),
    KitFingerprint(
        name="Caffeine",
        notes="Phishing-as-a-service; M365 and consumer service focus.",
        html_patterns=(
            ("caffeine-banner", re.compile(r"powered by caffeine|caffeine\.phish", re.I)),
        ),
        css_classes=("caf-modal", "caf-input"),
        form_action_patterns=(
            ("caffeine-post", re.compile(r"/cf/(?:logme|submit)", re.I)),
        ),
    ),
    KitFingerprint(
        name="Tycoon-2FA",
        notes="AiTM kit for M365; uses obfuscated JS and Cloudflare turnstile bypass.",
        html_patterns=(
            ("tycoon-marker", re.compile(r"tycoon[-_]?(?:2fa|panel|kit)", re.I)),
            ("turnstile-bypass", re.compile(r"cf_chl_(?:gen|cap)_tk", re.I)),
        ),
        asset_url_patterns=(
            ("tycoon-cdn", re.compile(r"//[a-z0-9-]+\.(?:pinata|fleek|ipfs)\.io/[a-z0-9]{20,}", re.I)),
        ),
    ),
    KitFingerprint(
        name="GreatHorn-clone",
        notes="Generic credential-harvest kit; many variants — looks for hallmark structure.",
        html_patterns=(
            ("greathorn-comment", re.compile(r"<!--\s*gh[-_](?:phish|kit|v\d)", re.I)),
        ),
        hidden_input_names=("gh_auth", "gh_session", "gh_tracker"),
    ),
    KitFingerprint(
        name="ModlishkaProxy",
        notes="Open-source reverse-proxy kit by Piotr Duszyński; old but still seen.",
        html_patterns=(
            ("modlishka-cookie", re.compile(r"document\.cookie\s*=\s*['\"]modlishka", re.I)),
        ),
        asset_url_patterns=(
            ("modlishka-path", re.compile(r"/__modlishka", re.I)),
        ),
    ),
)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def fingerprint(inspection: InspectionResult) -> list[KitMatch]:
    """Run the suspect's rendered DOM against every known kit fingerprint.

    Returns matches sorted by confidence descending. An empty list means no
    known kit was matched — not that the page is safe.
    """
    if not inspection.dom_hash:
        return []
    try:
        dom_bytes = read_blob(inspection.dom_hash, ".html")
    except FileNotFoundError:
        return []
    return fingerprint_dom(dom_bytes)


def fingerprint_dom(dom_bytes: bytes) -> list[KitMatch]:
    """Fingerprint a raw DOM byte string. Exposed for testing."""
    dom_text = dom_bytes.decode("utf-8", errors="replace")
    matches: list[KitMatch] = []

    try:
        soup = BeautifulSoup(dom_text, "html.parser")
    except Exception:  # noqa: BLE001
        soup = None

    for kit in _KIT_DB:
        hits = list(_match_kit(kit, dom_text, soup))
        if not hits:
            continue
        # Confidence scales with hit count and kit specificity. Two distinct
        # signatures = high confidence; one signature = medium.
        if len(hits) >= 2:
            conf = min(1.0, 0.55 + 0.15 * (len(hits) - 1))
        else:
            conf = 0.45
        matches.append(
            KitMatch(
                kit_name=kit.name,
                confidence=round(conf, 3),
                signatures_hit=hits,
                notes=kit.notes,
            )
        )

    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches


# --------------------------------------------------------------------------- #
# Per-kit matcher
# --------------------------------------------------------------------------- #


def _match_kit(
    kit: KitFingerprint,
    dom_text: str,
    soup: BeautifulSoup | None,
) -> Iterable[str]:
    """Yield the labels of every signature in ``kit`` that matches."""
    for label, rx in kit.html_patterns:
        if rx.search(dom_text):
            yield label

    if soup is not None:
        # CSS class signatures
        for css_class in kit.css_classes:
            if soup.find(class_=css_class):
                yield f"css:{css_class}"

        # Form action paths
        for label, rx in kit.form_action_patterns:
            for form in soup.find_all("form"):
                action = form.get("action") or ""
                if rx.search(action):
                    yield label
                    break

        # Hidden input names
        for name in kit.hidden_input_names:
            inp = soup.find("input", attrs={"name": name, "type": "hidden"})
            if inp is not None:
                yield f"hidden:{name}"

        # Asset URLs (src/href on any element)
        for label, rx in kit.asset_url_patterns:
            for tag in soup.find_all(["script", "link", "img", "iframe"]):
                src = tag.get("src") or tag.get("href") or ""
                if rx.search(src):
                    yield label
                    break


# --------------------------------------------------------------------------- #
# JS bundle hash matching (separate path — operates on InspectionResult)
# --------------------------------------------------------------------------- #


# Known-bad JS bundle hashes. Real production maintains hundreds of these.
_KNOWN_BAD_BUNDLES: dict[str, str] = {
    "a3f9b21c2c8d1f73": "16Shop main bundle (variant 2024-Q3)",
    "e72b9fc4901aa315": "EvilProxy session relay shim",
    "94d8f01b3e2c1a90": "Caffeine UI overlay",
    "6f12e08d5c93b471": "Tycoon-2FA turnstile bypass",
}


def check_js_bundles(inspection: InspectionResult) -> list[KitMatch]:
    """Return matches against known-bad JavaScript bundle hashes."""
    hits: list[KitMatch] = []
    for bundle_hash in inspection.js_bundle_hashes:
        if bundle_hash in _KNOWN_BAD_BUNDLES:
            label = _KNOWN_BAD_BUNDLES[bundle_hash]
            kit_name = label.split(" ", 1)[0]
            hits.append(
                KitMatch(
                    kit_name=kit_name,
                    confidence=0.9,  # Bundle-hash matches are very high confidence
                    signatures_hit=[f"bundle:{bundle_hash}"],
                    notes=label,
                )
            )
    return hits
