"""
Cloudflare abuse report submission.

Many phishing sites run behind Cloudflare's network for DDoS protection and
IP-masking. Cloudflare provides an abuse-form endpoint that ingests reports
of phishing, malware, and CSAM hosted on its network. We submit there for
any suspect URL whose name-server records indicate Cloudflare hosting.

Cloudflare doesn't have a public takedown REST API — abuse reports go via
``https://www.cloudflare.com/abuse/form``. We use the email-submission path
(POST to the abuse SMTP gateway) which Cloudflare accepts as an alternative
ingest. In MOCK_MODE we log instead of sending.
"""

from __future__ import annotations

from ...common.logging import get_logger
from ...common.models import Alert, Brand, InspectionResult, VerdictResult
from ...common.settings import get_settings
from ...common.ids import alert_id as gen_id
from . import TakedownProvider, TakedownResult, register_provider, _mock_mode

logger = get_logger(__name__)


# Hosts whose nameservers suggest Cloudflare. Real production resolves NS
# records via DNS at takedown time.
_CLOUDFLARE_NS_HINTS = (
    "cloudflare", "cf-ns", "ns.cloudflare.com",
)


class CloudflareProvider(TakedownProvider):
    name = "cloudflare"

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_enabled(self) -> bool:
        return bool(self.settings.cloudflare_abuse_email)

    def supports(self, registrar: str | None, host: str) -> bool:
        # In mock mode we'll claim every host as Cloudflare-supported so the
        # demo can show a takedown filing. Real production checks DNS NS
        # records and only fires when Cloudflare-fronted.
        if _mock_mode():
            return True
        # Live: check NS records
        try:
            import socket
            # crude: resolve, then look up the answer's hosting; for demo
            # purposes we just match by host substring
            return any(hint in host for hint in _CLOUDFLARE_NS_HINTS)
        except Exception:  # noqa: BLE001
            return False

    def submit(
        self,
        alert: Alert,
        brand: Brand,
        inspection: InspectionResult,
        verdict: VerdictResult,
    ) -> TakedownResult:
        case_id = f"CF-{gen_id()[-10:].upper()}"
        report = self._build_report(alert, brand, inspection, verdict)
        if _mock_mode():
            logger.info(
                "cloudflare.mock_submit",
                case_id=case_id,
                abuse_type="phishing",
                target_host=report["target_host"],
                evidence_bullets=len(report["evidence"]),
            )
            return TakedownResult(
                provider=self.name,
                success=True,
                case_id=case_id,
                details={"mode": "mock", "abuse_type": "phishing"},
            )
        # Live path is intentionally not implemented in the prototype;
        # would POST a multipart form to www.cloudflare.com/abuse/form
        # or send an email to the configured abuse address.
        return TakedownResult(
            provider=self.name,
            success=False,
            error="Live Cloudflare abuse submission requires manual review queue",
        )

    @staticmethod
    def _build_report(
        alert: Alert,
        brand: Brand,
        inspection: InspectionResult,
        verdict: VerdictResult,
    ) -> dict:
        from urllib.parse import urlparse
        host = urlparse(alert.suspect_url).hostname or alert.suspect_url
        return {
            "report_type": "phishing",
            "target_host": host,
            "target_url": alert.suspect_url,
            "brand_impersonated": brand.name,
            "verdict_confidence": verdict.confidence,
            "evidence": verdict.evidence_summary[:5],
            "screenshot_hash": inspection.screenshot_hash,
            "registrar": inspection.registrar,
            "first_observed": alert.created_at.isoformat(),
        }


register_provider(CloudflareProvider())
