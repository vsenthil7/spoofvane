"""
GoDaddy takedown submission.

GoDaddy publishes a Reseller / Abuse API at ``api.godaddy.com``. Their
abuse-reporting endpoint accepts JSON with structured evidence. We construct
the request here.

In MOCK_MODE we log; live mode is a stub.
"""

from __future__ import annotations

from ...common.logging import get_logger
from ...common.models import Alert, Brand, InspectionResult, VerdictResult
from ...common.settings import get_settings
from ...common.ids import alert_id as gen_id
from . import TakedownProvider, TakedownResult, register_provider, _mock_mode

logger = get_logger(__name__)


class GoDaddyProvider(TakedownProvider):
    name = "godaddy"

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_enabled(self) -> bool:
        return bool(self.settings.godaddy_api_key and self.settings.godaddy_api_secret)

    def supports(self, registrar: str | None, host: str) -> bool:
        if registrar and "godaddy" in registrar.lower():
            return True
        return False

    def submit(
        self,
        alert: Alert,
        brand: Brand,
        inspection: InspectionResult,
        verdict: VerdictResult,
    ) -> TakedownResult:
        case_id = f"GD-{gen_id()[-10:].upper()}"
        payload = self._build_payload(alert, brand, inspection, verdict)
        if _mock_mode():
            logger.info(
                "godaddy.mock_submit",
                case_id=case_id,
                target_domain=payload["domain"],
                evidence_bullets=len(payload["info"]),
                registrar=inspection.registrar,
            )
            return TakedownResult(
                provider=self.name,
                success=True,
                case_id=case_id,
                details={"mode": "mock", "endpoint": "api.godaddy.com/v1/abuse/tickets"},
            )
        return TakedownResult(
            provider=self.name,
            success=False,
            error="Live GoDaddy abuse submission requires API approval",
        )

    @staticmethod
    def _build_payload(
        alert: Alert,
        brand: Brand,
        inspection: InspectionResult,
        verdict: VerdictResult,
    ) -> dict:
        from urllib.parse import urlparse
        host = urlparse(alert.suspect_url).hostname or alert.suspect_url
        return {
            "type": "PHISHING",
            "domain": host,
            "target": brand.name,
            "info": verdict.evidence_summary[:8],
            "infoUrl": alert.suspect_url,
            "intentional": True,
            "proxy": False,
            "source": "spoofvane",
        }


register_provider(GoDaddyProvider())
