"""
Namecheap takedown submission.

Namecheap is a popular registrar for phishing operators because it accepts
cryptocurrency and minimal KYC. They publish an XML API for account
operations; abuse reports go through ``abuse@namecheap.com`` with structured
evidence attached. We generate the email body + JSON payload here.

In MOCK_MODE we log; live mode is a stub for the prototype.
"""

from __future__ import annotations

from ...common.logging import get_logger
from ...common.models import Alert, Brand, InspectionResult, VerdictResult
from ...common.settings import get_settings
from ...common.ids import alert_id as gen_id
from . import TakedownProvider, TakedownResult, register_provider, _mock_mode

logger = get_logger(__name__)


class NamecheapProvider(TakedownProvider):
    name = "namecheap"

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_enabled(self) -> bool:
        return bool(self.settings.namecheap_api_user and self.settings.namecheap_api_key)

    def supports(self, registrar: str | None, host: str) -> bool:
        if registrar and "namecheap" in registrar.lower():
            return True
        # When registrar metadata is missing we don't guess
        return False

    def submit(
        self,
        alert: Alert,
        brand: Brand,
        inspection: InspectionResult,
        verdict: VerdictResult,
    ) -> TakedownResult:
        case_id = f"NC-{gen_id()[-10:].upper()}"
        body = self._build_request(alert, brand, inspection, verdict)
        if _mock_mode():
            logger.info(
                "namecheap.mock_submit",
                case_id=case_id,
                target_domain=body["target_domain"],
                evidence_bullets=len(body["evidence"]),
                registrar=inspection.registrar,
            )
            return TakedownResult(
                provider=self.name,
                success=True,
                case_id=case_id,
                details={"mode": "mock", "via": "abuse@namecheap.com"},
            )
        return TakedownResult(
            provider=self.name,
            success=False,
            error="Live Namecheap submission requires verified API account",
        )

    @staticmethod
    def _build_request(
        alert: Alert,
        brand: Brand,
        inspection: InspectionResult,
        verdict: VerdictResult,
    ) -> dict:
        from urllib.parse import urlparse
        host = urlparse(alert.suspect_url).hostname or alert.suspect_url
        return {
            "target_domain": host,
            "abuse_category": "phishing",
            "brand_impersonated": brand.name,
            "first_observed": alert.created_at.isoformat(),
            "verdict_confidence": verdict.confidence,
            "evidence": verdict.evidence_summary[:8],
            "spoofvane_alert_id": alert.id,
        }


register_provider(NamecheapProvider())
