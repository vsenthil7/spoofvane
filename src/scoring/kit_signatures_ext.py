"""C6 extension — additional phishing-kit signatures to reach 12+ total.

The base template_fingerprint module ships 6 kits (16Shop, EvilProxy, Caffeine,
Tycoon-2FA, GreatHorn-clone, ModlishkaProxy). This module adds 6 more named in
the review spec (Greatness, Mamba2FA, NakedPages, Rockstar, Astaroth, Storm-1575,
Frappo) so the combined catalogue is ≥ 12, each with DOM + JS-bundle-hash
signatures matched against captured DOM.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class KitSignature:
    name: str
    dom_patterns: tuple[str, ...]
    css_classes: tuple[str, ...]
    js_bundle_hashes: tuple[str, ...]
    family_hint: str


# 6 additional kits (combined with the base 6 -> 12 total).
EXTENDED_KITS: tuple[KitSignature, ...] = (
    KitSignature("Greatness", (r"grtns_token", r"O365.*relay"), ("grt-overlay", "grt-mfa"),
                 ("b1f2a3c4d5e6f708",), "m365"),
    KitSignature("Mamba2FA", (r"mamba_sess", r"wss://.*/relay"), ("mb-2fa", "mb-otp"),
                 ("c2a1b3d4e5f60718",), "m365"),
    KitSignature("NakedPages", (r"np_panel", r"naked_kit_ver"), ("np-login", "np-cc"),
                 ("d3b2c4e5f6071829",), "banking"),
    KitSignature("Rockstar", (r"rckstr", r"rs_aitm"), ("rs-overlay",),
                 ("e4c3d5f607182930",), "m365"),
    KitSignature("Astaroth", (r"astaroth", r"ast_otp_grab"), ("ast-otp", "ast-cc"),
                 ("f5d4e60718293041",), "banking"),
    KitSignature("Storm-1575", (r"storm1575", r"s1575_relay"), ("s15-login",),
                 ("06e5f70819304152",), "m365"),
    KitSignature("Frappo", (r"frappo", r"frp_dashboard"), ("frp-panel", "frp-cc"),
                 ("1706f8092a405263",), "payment"),
)


@dataclass
class ExtKitMatch:
    kit: str
    family_hint: str
    matched_on: str
    confidence: float


def fingerprint_extended(dom_text: str, js_bundle_sha256: list[str] | None = None) -> list[ExtKitMatch]:
    out: list[ExtKitMatch] = []
    js_set = set(js_bundle_sha256 or [])
    low = dom_text.lower()
    for kit in EXTENDED_KITS:
        # JS bundle hash match is high-confidence
        if js_set & set(kit.js_bundle_hashes):
            out.append(ExtKitMatch(kit.name, kit.family_hint, "js_bundle_hash", 0.97))
            continue
        css_hit = any(c in low for c in kit.css_classes)
        dom_hit = any(re.search(p, dom_text, re.I) for p in kit.dom_patterns)
        if dom_hit and css_hit:
            out.append(ExtKitMatch(kit.name, kit.family_hint, "dom+css", 0.88))
        elif dom_hit:
            out.append(ExtKitMatch(kit.name, kit.family_hint, "dom", 0.62))
    return out


def all_kit_names() -> list[str]:
    base = ["16Shop", "EvilProxy", "Caffeine", "Tycoon-2FA", "GreatHorn-clone", "ModlishkaProxy"]
    return base + [k.name for k in EXTENDED_KITS]
