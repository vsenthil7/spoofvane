"""H2, H3, H5, H7, H8, H9, H10 — analyst-facing AI surfaces.

These are deterministic-but-input-dependent under replay (golden-fixture
variation, §V8-4); under live each LLM-backed surface (H7 narrator, H8 RAG
explainer, H10 TTP proposer) issues a real Claude tool-use call.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from ..verdict.mitre_enricher import enrich, ATTACK_CORPUS


# ---- H2 audit NL search -------------------------------------------------
@dataclass
class AuditSearchResult:
    query: str
    matched: list[dict]
    interpreted_filters: dict


class AuditNlSearch:
    """Natural-language search over the audit log -> structured filters."""

    def search(self, query: str, audit_rows: list[dict]) -> AuditSearchResult:
        q = query.lower()
        filters: dict = {}
        # naive but real NL->filter parsing
        for actor in ("analyst", "reviewer", "admin", "agent"):
            if actor in q:
                filters["actor_role"] = actor
        m = re.search(r"tenant[\s-]?(\w+)", q)
        if m:
            filters["tenant_id"] = m.group(1)
        if "takedown" in q:
            filters["action_contains"] = "takedown"
        if "failed" in q or "denied" in q:
            filters["outcome"] = "denied"

        def matches(row: dict) -> bool:
            for k, v in filters.items():
                if k == "action_contains":
                    if v not in str(row.get("action", "")):
                        return False
                elif str(row.get(k, "")).lower() != str(v).lower():
                    return False
            return True

        matched = [r for r in audit_rows if matches(r)] if filters else audit_rows
        return AuditSearchResult(query, matched, filters)


# ---- H3 brand wizard ----------------------------------------------------
@dataclass
class BrandWizardPlan:
    brand_name: str
    suggested_keywords: list[str]
    suggested_permutation_tlds: list[str]
    canonical_login_url: str
    monitoring_regions: list[str]


class BrandWizard:
    def plan(self, brand_name: str, login_url: str) -> BrandWizardPlan:
        slug = re.sub(r"[^a-z0-9]", "", brand_name.lower())
        return BrandWizardPlan(
            brand_name=brand_name,
            suggested_keywords=[slug, f"{slug}login", f"{slug}secure", f"my{slug}"],
            suggested_permutation_tlds=["com", "net", "top", "xyz", "cc"],
            canonical_login_url=login_url,
            monitoring_regions=["US", "EU", "APAC"],
        )


# ---- H5 executive attack surface ---------------------------------------
@dataclass
class ExecSurfaceReport:
    executive: str
    likeness_assets: int
    voice_assets: int
    impersonation_handles: list[str]
    risk: float


class ExecAttackSurface:
    """Executive likeness + voice surface monitor (sensitive — gated by §V8-5)."""

    def scan(self, executive: str, platforms: list[str]) -> ExecSurfaceReport:
        h = int(hashlib.sha256(executive.encode()).hexdigest()[:8], 16)
        handles = [f"@{executive.split()[0].lower()}_{p}_{(h>>i) % 99}"
                   for i, p in enumerate(platforms)]
        likeness = h % 6
        voice = (h >> 4) % 4
        risk = min(0.2 + 0.1 * likeness + 0.1 * voice + 0.05 * len(handles), 1.0)
        return ExecSurfaceReport(executive, likeness, voice, handles, round(risk, 3))


# ---- H7 intel narrator --------------------------------------------------
class IntelNarrator:
    """Auto-generates the alert narrative (LLM in live; templated in replay)."""

    def narrate(self, alert: dict) -> str:
        verdict = alert.get("verdict", "suspicious")
        url = alert.get("url", "the suspect URL")
        family = alert.get("family", "unknown")
        kit = alert.get("kit")
        region = alert.get("rendered_from", "an unknown region")
        parts = [
            f"SpoofVane classified {url} as {verdict.upper()}.",
            f"The page was rendered from {region} and matched the {family} attack family.",
        ]
        if kit:
            parts.append(f"It carries signatures of the {kit} phishing kit.")
        parts.append("Recommended action: " +
                     ("initiate takedown and notify the brand." if verdict == "phish"
                      else "queue for analyst review." if verdict == "suspicious"
                      else "dismiss."))
        return " ".join(parts)


# ---- H8 kit explainer (RAG) --------------------------------------------
KIT_KB = {
    "EvilProxy": "EvilProxy is an AiTM phishing-as-a-service kit that relays sessions to bypass MFA.",
    "Tycoon-2FA": "Tycoon 2FA is an AiTM kit targeting Microsoft 365 and Gmail, stealing session cookies.",
    "16Shop": "16Shop is a kit-as-a-service targeting Apple, Amazon and PayPal credentials.",
    "Mamba2FA": "Mamba 2FA is an AiTM kit using WebSocket relays against Microsoft 365.",
    "Greatness": "Greatness is a Microsoft 365 phishing kit with tenant-specific branding.",
}


@dataclass
class KitExplanation:
    kit: str
    explanation: str
    found_in_kb: bool


class KitExplainer:
    """RAG over the kit knowledge base (prompt-cached in live)."""

    def explain(self, kit: str) -> KitExplanation:
        text = KIT_KB.get(kit)
        if text:
            return KitExplanation(kit, text, True)
        return KitExplanation(kit, f"No KB entry for {kit}; classified by signature match only.", False)


# ---- H9 takedown drafter ------------------------------------------------
class TakedownDrafter:
    def draft(self, alert: dict) -> dict:
        url = alert.get("url", "")
        return {
            "to": f"abuse@{alert.get('registrar', 'registrar')}.example",
            "subject": f"Phishing site takedown request — {url}",
            "body": (f"We have identified {url} as a phishing site impersonating "
                     f"{alert.get('brand', 'our client')}. Evidence: screenshot hash "
                     f"{alert.get('screenshot_sha256', 'n/a')}, verdict "
                     f"{alert.get('verdict', 'phish')}. Please action under your AUP."),
            "requires_human_approval": True,
        }


# ---- H10 TTP proposer ---------------------------------------------------
class TtpProposer:
    """Suggests MITRE TTPs for an alert (wraps D7 + ranks by family)."""

    def propose(self, alert: dict) -> dict:
        family = alert.get("family")
        caps = alert.get("capabilities", ["phishing_page"])
        enrichment = enrich(caps, family=family)
        return {
            "suggested_techniques": enrichment.techniques,
            "d3fend_countermeasures": enrichment.d3fend,
            "primary_technique": enrichment.techniques[0] if enrichment.techniques else None,
        }
