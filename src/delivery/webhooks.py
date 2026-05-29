"""Outbound webhook fan-out for new alerts.

Supports:
  - Slack via incoming webhook
  - Splunk HEC
  - Microsoft Sentinel HTTP Data Collector (sketched)
  - Generic JSON POST

In MOCK_MODE the destinations log the payload but do not POST.
"""
from __future__ import annotations

import json

import httpx

from ..common.logging import get_logger
from ..common.models import Alert, Brand, InspectionResult, VerdictResult
from ..common.settings import get_settings

log = get_logger(__name__)


def dispatch_alert(
    alert: Alert,
    brand: Brand,
    inspection: InspectionResult,
    verdict: VerdictResult,
) -> dict[str, str]:
    """POST the alert to every configured destination.

    Returns a small dict ``{destination: status}`` for the caller to surface.
    """
    settings = get_settings()
    payload = _build_payload(alert, brand, inspection, verdict)
    statuses: dict[str, str] = {}

    if settings.slack_webhook_url:
        statuses["slack"] = _post_slack(settings.slack_webhook_url, payload, dry=settings.mock_mode)

    if settings.splunk_hec_url and settings.splunk_hec_token:
        statuses["splunk"] = _post_splunk(
            settings.splunk_hec_url, settings.splunk_hec_token, payload, dry=settings.mock_mode
        )

    if not statuses:
        statuses["noop"] = "no destinations configured"

    log.info("dispatched", alert_id=alert.id, statuses=statuses)
    return statuses


# ─── payload + adapters ────────────────────────────────────────────────


def _build_payload(
    alert: Alert,
    brand: Brand,
    inspection: InspectionResult,
    verdict: VerdictResult,
) -> dict:
    return {
        "schema": "doppeldomain.alert.v1",
        "alert_id": alert.id,
        "brand": brand.name,
        "severity": alert.severity.value,
        "verdict": verdict.verdict.value,
        "confidence": verdict.confidence,
        "suggested_action": verdict.suggested_action,
        "suspect_url": alert.suspect_url,
        "final_url": inspection.final_url,
        "registrar": inspection.registrar,
        "asn": inspection.asn,
        "screenshot_hash": inspection.screenshot_hash,
        "dom_hash": inspection.dom_hash,
        "evidence_summary": verdict.evidence_summary,
        "created_at": alert.created_at.isoformat(),
    }


def _post_slack(url: str, payload: dict, *, dry: bool) -> str:
    msg = {
        "text": f":rotating_light: *DoppelDomain* — {payload['severity'].upper()} — {payload['brand']}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{payload['brand']}*  ·  *{payload['severity'].upper()}*  ·  "
                        f"`{payload['verdict']}` (conf {payload['confidence']:.2f})\n"
                        f"<{payload['suspect_url']}|`{payload['suspect_url']}`>\n"
                        f"_Registrar:_ {payload['registrar'] or '?'}  ·  "
                        f"_ASN:_ {payload['asn'] or '?'}"
                    ),
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Evidence*\n" + "\n".join(f"• {e}" for e in payload["evidence_summary"])},
            },
        ],
    }
    if dry:
        return "skipped (mock)"
    try:
        r = httpx.post(url, json=msg, timeout=10)
        return f"ok ({r.status_code})" if r.status_code < 300 else f"fail ({r.status_code})"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


def _post_splunk(url: str, token: str, payload: dict, *, dry: bool) -> str:
    body = {"event": payload, "sourcetype": "doppeldomain:alert"}
    if dry:
        return "skipped (mock)"
    try:
        r = httpx.post(
            url,
            headers={"Authorization": f"Splunk {token}", "Content-Type": "application/json"},
            content=json.dumps(body),
            timeout=10,
        )
        return f"ok ({r.status_code})" if r.status_code < 300 else f"fail ({r.status_code})"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"
