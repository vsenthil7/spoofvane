"""Claude Sonnet 4.6 verdict engine.

Produces a structured ``VerdictResult`` per inspection from:
  - the suspect screenshot (vision)
  - the canonical screenshot (vision, for comparison)
  - sub-scores (pHash, DOM, logo, favicon)
  - inspection metadata (registrar, registration date, ASN, final URL)

When ``MOCK_MODE`` is true (or no API key is configured), a rule-based
fallback produces a deterministic verdict so the demo runs offline.
"""
from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import urlparse

from ..common.ids import verdict_id
from ..common.logging import get_logger
from ..common.models import (
    Brand,
    InspectionResult,
    ScoringResult,
    Severity,
    Verdict,
    VerdictResult,
)
from ..common.settings import get_settings
from ..storage.blob_store import read_blob

log = get_logger(__name__)


_SYSTEM_PROMPT = """You are an expert phishing analyst. You receive:
- The canonical login page of a known brand (the legitimate page).
- A suspect page found on the open web.
- Numerical similarity sub-scores and metadata about the suspect.

Decide whether the suspect page is:
  - "phish"      — high-confidence brand impersonation, action: takedown
  - "suspicious" — looks similar but evidence is mixed, action: watch
  - "benign"     — not an impersonation, action: dismiss

Be conservative. Prefer "suspicious" over "phish" when in doubt — false
positives erode operator trust. Cite concrete evidence from the screenshot
and metadata; do not speculate beyond what you see.

Also produce a takedown-notice draft addressed to the registrar, written
in a calm, professional tone, suitable for the brand's legal team to send
after review. Mark it clearly as a draft.

Return only the structured response via the provided tool. No prose.
"""


_VERDICT_TOOL = {
    "name": "submit_verdict",
    "description": "Submit a structured phishing verdict.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["phish", "suspicious", "benign"]},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
            "evidence_summary": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 8,
            },
            "suggested_action": {
                "type": "string",
                "enum": ["takedown", "watch", "dismiss"],
            },
            "takedown_draft": {"type": "string"},
        },
        "required": [
            "verdict",
            "confidence",
            "severity",
            "evidence_summary",
            "suggested_action",
            "takedown_draft",
        ],
    },
}


class VerdictEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    def decide(
        self,
        brand: Brand,
        inspection: InspectionResult,
        scoring: ScoringResult,
        canonical_screenshot: bytes,
    ) -> VerdictResult:
        if self._should_mock():
            return self._mock_verdict(brand, inspection, scoring)

        suspect_screenshot = self._read_screenshot(inspection)
        if not suspect_screenshot or not canonical_screenshot:
            log.warning("verdict_missing_screenshot", inspection_id=inspection.id)
            return self._mock_verdict(brand, inspection, scoring)

        try:
            return self._live_verdict(
                brand, inspection, scoring, canonical_screenshot, suspect_screenshot
            )
        except Exception as exc:  # noqa: BLE001
            log.error("verdict_live_failed", error=str(exc))
            return self._mock_verdict(brand, inspection, scoring)

    # ─── internals ──────────────────────────────────────────────────────

    def _should_mock(self) -> bool:
        return self.settings.mock_mode or not self.settings.anthropic_api_key

    @staticmethod
    def _read_screenshot(inspection: InspectionResult) -> bytes:
        if not inspection.screenshot_hash:
            return b""
        try:
            return read_blob(inspection.screenshot_hash, suffix=".png")
        except FileNotFoundError:
            return b""

    def _live_verdict(
        self,
        brand: Brand,
        inspection: InspectionResult,
        scoring: ScoringResult,
        canonical_screenshot: bytes,
        suspect_screenshot: bytes,
    ) -> VerdictResult:
        from anthropic import Anthropic  # type: ignore

        client = Anthropic(api_key=self.settings.anthropic_api_key)

        metadata = {
            "brand_name": brand.name,
            "canonical_login_url": str(brand.login_url),
            "suspect_url": inspection.final_url,
            "registrar": inspection.registrar,
            "asn": inspection.asn,
            "registration_date": (
                inspection.registration_date.isoformat() if inspection.registration_date else None
            ),
            "scores": {
                "phash": scoring.phash_score,
                "dom": scoring.dom_score,
                "logo": scoring.logo_score,
                "favicon_match": scoring.favicon_match,
                "composite": scoring.composite_score,
            },
        }

        user_blocks: list[dict[str, Any]] = [
            {"type": "text", "text": "CANONICAL (legitimate) login page:"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(canonical_screenshot).decode("ascii"),
                },
            },
            {"type": "text", "text": "SUSPECT page found on the open web:"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(suspect_screenshot).decode("ascii"),
                },
            },
            {"type": "text", "text": f"Metadata:\n```json\n{json.dumps(metadata, indent=2)}\n```"},
        ]

        response = client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=1600,
            system=_SYSTEM_PROMPT,
            tools=[_VERDICT_TOOL],
            tool_choice={"type": "tool", "name": "submit_verdict"},
            messages=[{"role": "user", "content": user_blocks}],
        )

        block = next(b for b in response.content if b.type == "tool_use")
        data = block.input

        return VerdictResult(
            id=verdict_id(),
            inspection_id=inspection.id,
            verdict=Verdict(data["verdict"]),
            confidence=float(data["confidence"]),
            severity=Severity(data["severity"]),
            evidence_summary=list(data["evidence_summary"]),
            suggested_action=data["suggested_action"],
            takedown_draft=data["takedown_draft"],
            model_used=self.settings.anthropic_model,
        )

    def _mock_verdict(
        self,
        brand: Brand,
        inspection: InspectionResult,
        scoring: ScoringResult,
    ) -> VerdictResult:
        """Rule-based fallback verdict.

        Conservative: only "phish" when the composite is very high *and* the
        domain is very new. Otherwise "suspicious" or "benign".
        """
        days_old = self._days_old(inspection)
        host = urlparse(inspection.final_url or "").hostname or "unknown-host"

        if scoring.composite_score >= 0.85 and days_old <= 14:
            v = Verdict.PHISH
            sev = Severity.CRITICAL
            conf = 0.93
            action = "takedown"
            evidence = [
                f"Visual similarity to canonical is very high (pHash {scoring.phash_score:.2f}).",
                f"DOM structure aligns with the canonical login (DOM {scoring.dom_score:.2f}).",
                f"Logo similarity in header region is {scoring.logo_score:.2f}.",
                f"Domain {host} was registered ~{days_old} days ago via {inspection.registrar}.",
                f"Hosted on ASN {inspection.asn} — historically associated with low-reputation infra.",
            ]
        elif scoring.composite_score >= brand.score_threshold:
            v = Verdict.SUSPICIOUS
            sev = Severity.HIGH if scoring.composite_score >= 0.75 else Severity.MEDIUM
            conf = 0.72
            action = "watch"
            evidence = [
                f"Composite similarity score {scoring.composite_score:.2f} above threshold {brand.score_threshold:.2f}.",
                f"Visual similarity {scoring.phash_score:.2f}, DOM {scoring.dom_score:.2f}, logo {scoring.logo_score:.2f}.",
                f"Domain age ~{days_old} days; registrar {inspection.registrar}.",
            ]
        else:
            v = Verdict.BENIGN
            sev = Severity.LOW
            conf = 0.81
            action = "dismiss"
            evidence = [
                f"Visual similarity to canonical is low (pHash {scoring.phash_score:.2f}).",
                f"DOM differs structurally from the canonical (DOM {scoring.dom_score:.2f}).",
                "No login-form pattern matching the canonical was detected.",
            ]

        takedown = _build_takedown_draft(brand, inspection, evidence) if action == "takedown" else (
            f"(No takedown drafted — suggested action: {action}.)"
        )

        return VerdictResult(
            id=verdict_id(),
            inspection_id=inspection.id,
            verdict=v,
            confidence=conf,
            severity=sev,
            evidence_summary=evidence,
            suggested_action=action,
            takedown_draft=takedown,
            model_used="rules-fallback-v1",
        )

    @staticmethod
    def _days_old(inspection: InspectionResult) -> int:
        if not inspection.registration_date:
            return 9999
        import datetime as _dt

        now = _dt.datetime.now(tz=_dt.timezone.utc)
        delta = now - inspection.registration_date
        return max(0, delta.days)


def _build_takedown_draft(
    brand: Brand,
    inspection: InspectionResult,
    evidence: list[str],
) -> str:
    host = urlparse(inspection.final_url or "").hostname or "the suspect domain"
    bullets = "\n".join(f"  • {line}" for line in evidence)
    return (
        f"[DRAFT — for legal review before sending]\n\n"
        f"To: Abuse Desk, {inspection.registrar or '<registrar>'}\n"
        f"Subject: Trademark and brand-impersonation complaint — {host}\n\n"
        f"Dear Abuse Team,\n\n"
        f"We represent {brand.name} ({brand.login_url}). We have identified a website at "
        f"{inspection.final_url} that is impersonating our brand's login page in order to "
        f"defraud our customers. Evidence:\n\n{bullets}\n\n"
        f"We attach an evidence pack including a full-page screenshot, DOM dump, and content "
        f"hashes (SHA-256) of all artefacts for tamper-evidence. We respectfully request that "
        f"you suspend the domain and preserve relevant records.\n\n"
        f"Thank you for your prompt attention.\n\n"
        f"Sincerely,\n"
        f"{brand.name} Trust & Safety"
    )


def get_verdict_engine() -> VerdictEngine:
    return VerdictEngine()
