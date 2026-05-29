"""Webhook dispatch: payload shape and mock-mode safety."""

from src.common.ids import alert_id, inspection_id, suspect_id, verdict_id
from src.common.models import (
    Alert,
    AlertStatus,
    Brand,
    InspectionResult,
    Severity,
    Verdict,
    VerdictResult,
)
from src.delivery.webhooks import dispatch_alert


def _bundle() -> tuple[Alert, Brand, InspectionResult, VerdictResult]:
    brand = Brand(
        id="brand_x", name="X", login_url="https://login.x.example/signin", target_country="US"
    )
    insp = InspectionResult(
        id=inspection_id(),
        suspect_url_id=suspect_id(),
        success=True,
        rendered_country="US",
        final_url="https://account-update-portal.xyz/login",
    )
    verdict = VerdictResult(
        id=verdict_id(),
        inspection_id=insp.id,
        verdict=Verdict.PHISH,
        confidence=0.93,
        severity=Severity.CRITICAL,
        evidence_summary=["pixel-perfect clone", "domain age 3 days"],
        suggested_action="takedown",
        takedown_draft="[DRAFT — for legal review]\n\nDear registrar,\n…",
        model_used="claude-sonnet-4-6",
    )
    alert = Alert(
        id=alert_id(),
        brand_id=brand.id,
        inspection_id=insp.id,
        verdict_id=verdict.id,
        severity=Severity.CRITICAL,
        status=AlertStatus.OPEN,
        suspect_url="https://account-update-portal.xyz/login",
    )
    return alert, brand, insp, verdict


def test_dispatch_runs_clean_in_mock_mode() -> None:
    alert, brand, insp, verdict = _bundle()
    results = dispatch_alert(alert, brand, insp, verdict)
    # All destinations should report "skipped" or similar non-error status
    assert isinstance(results, dict)
    for status in results.values():
        # Mock mode → no real HTTP, every destination is dry-run / skipped
        assert "error" not in status.lower()
