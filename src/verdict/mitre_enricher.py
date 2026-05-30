"""D7 — MITRE ATT&CK + D3FEND enrichment on every alert.

Maps alert features (kit family, capabilities observed) to real MITRE ATT&CK
technique IDs and suggested D3FEND countermeasures from a bundled corpus.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Bundled subset of real ATT&CK technique IDs relevant to phishing/impersonation.
ATTACK_CORPUS = {
    "phishing_page": ["T1566.002", "T1598.003"],     # Spearphishing Link / via Service
    "credential_harvest": ["T1056.003", "T1111"],     # Web Portal Capture / MFA Interception
    "aitm_relay": ["T1557", "T1539"],                  # AiTM / Steal Web Session Cookie
    "fake_app": ["T1660", "T1204.002"],                # Phishing (mobile) / Malicious File
    "deepfake_voice": ["T1656"],                       # Impersonation
    "brand_impersonation": ["T1583.001", "T1585.001"], # Domains / Social Media Accounts
}
D3FEND_MAP = {
    "T1566.002": ["D3-UA"],   # URL Analysis
    "T1557": ["D3-NTA"],      # Network Traffic Analysis
    "T1111": ["D3-MFA"],      # Multi-factor Authentication
    "T1656": ["D3-MA"],       # Message Authentication
}


@dataclass
class MitreEnrichment:
    techniques: list[str] = field(default_factory=list)
    technique_tactics: dict[str, str] = field(default_factory=dict)
    d3fend: list[str] = field(default_factory=list)


# v07 D5 — per-surface ATT&CK technique mapping. Each v07 width surface has a
# characteristic technique set, so a finding from any surface is TTP-tagged even
# when no explicit capability tags are present.
SURFACE_TECHNIQUES = {
    "domain": ["T1583.001", "T1566.002"],          # Acquire Domains / Spearphishing Link
    "social": ["T1585.001", "T1656"],              # Social Media Accounts / Impersonation
    "appstore": ["T1660", "T1204.002"],            # Phishing (mobile) / Malicious File
    "marketplace": ["T1583.008", "T1657"],         # Malvertising / Financial Theft
    "darkweb": ["T1597.002", "T1593.003"],         # Purchase Technical Data / Search
    "credleak": ["T1589.001", "T1078"],            # Credentials / Valid Accounts
    "easm": ["T1595.002", "T1590"],                # Vuln Scanning / Gather Victim Network
    "rtp": ["T1557", "T1539"],                     # AiTM / Steal Web Session Cookie
    "deepfake": ["T1656"],                          # Impersonation
    "email_auth": ["T1566.002", "T1598.003"],      # Spearphishing Link / via Service
}


def enrich_for_surface(surface: str, capabilities: list[str] | None = None,
                       family: str | None = None) -> MitreEnrichment:
    """v07 D5 — surface-aware enrichment. Seeds techniques from the surface's
    characteristic set, then layers capability/family-driven techniques on top
    via the existing enrich() logic. Distinct surfaces yield distinct TTP sets."""
    base = enrich(capabilities or [], family=family)
    techs = list(SURFACE_TECHNIQUES.get(surface, []))
    for t in base.techniques:
        if t not in techs:
            techs.append(t)
    d3: list[str] = []
    for t in techs:
        for d in D3FEND_MAP.get(t, []):
            if d not in d3:
                d3.append(d)
    return MitreEnrichment(techniques=techs, d3fend=d3)


def enrich(capabilities: list[str], family: str | None = None) -> MitreEnrichment:
    techs: list[str] = []
    caps = list(capabilities)
    if family in ("m365", "banking", "payment", "crypto"):
        caps.append("credential_harvest")
    caps.append("brand_impersonation")
    for cap in caps:
        for t in ATTACK_CORPUS.get(cap, []):
            if t not in techs:
                techs.append(t)
    d3 = []
    for t in techs:
        for d in D3FEND_MAP.get(t, []):
            if d not in d3:
                d3.append(d)
    return MitreEnrichment(techniques=techs, d3fend=d3)
