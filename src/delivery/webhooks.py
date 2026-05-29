"""Outbound webhook fan-out for new alerts.

Supports:
  - Slack via incoming webhook
  - Splunk HEC
  - Generic JSON POST with HMAC-SHA256 signature
  - ServiceNow incident creation
  - Microsoft Sentinel (Log Analytics Data Collector)
  - PagerDuty Events API v2
  - STIX/TAXII 2.1 indicator publishing

In MOCK_MODE the destinations log the payload but do not POST.

Outbound generic payloads are signed when ``settings.webhook_signing_secret``
is set. The signature is HMAC-SHA256 over the JSON body and is delivered in
the ``X-DoppelDomain-Signature: sha256=<hex>`` header. Receivers verify before
trusting the payload — protects against a stolen webhook URL being used to
spoof events.
"""
from __future__ import annotations

import hashlib
import hmac
import json

import httpx

from ..common.logging import get_logger
from ..common.models import Alert, Brand, InspectionResult, VerdictResult
from ..common.settings import get_settings
from . import pagerduty, sentinel, servicenow, taxii

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

    # --- Simple notification channels --------------------------------------
    if settings.slack_webhook_url:
        statuses["slack"] = _post_slack(settings.slack_webhook_url, payload, dry=settings.mock_mode)

    if settings.splunk_hec_url and settings.splunk_hec_token:
        statuses["splunk"] = _post_splunk(
            settings.splunk_hec_url, settings.splunk_hec_token, payload, dry=settings.mock_mode
        )

    if getattr(settings, "generic_webhook_url", ""):
        statuses["generic"] = _post_generic(
            settings.generic_webhook_url,
            payload,
            settings.webhook_signing_secret,
            dry=settings.mock_mode,
        )

    # --- Enterprise integrations ------------------------------------------
    # Each returns None when not configured. In mock mode we skip the network
    # call entirely.
    if not settings.mock_mode:
        sn = servicenow.send_alert_as_incident(alert, brand, inspection, verdict)
        if sn is not None:
            statuses["servicenow"] = _format(sn)

        sentinel_r = sentinel.send_alert_to_sentinel(alert, brand, inspection, verdict)
        if sentinel_r is not None:
            statuses["sentinel"] = _format(sentinel_r)

        pd = pagerduty.trigger_pagerduty(alert, brand, inspection, verdict)
        if pd is not None:
            statuses["pagerduty"] = _format(pd)

        tx = taxii.publish_to_taxii(alert, brand, inspection, verdict)
        if tx is not None:
            statuses["taxii"] = _format(tx)
    else:
        # In mock mode, surface which integrations *would* fire if configured
        # — purely so the demo dashboard / logs make the wiring visible.
        configured = []
        if settings.servicenow_instance: configured.append("servicenow")
        if settings.sentinel_workspace_id: configured.append("sentinel")
        if settings.pagerduty_routing_key: configured.append("pagerduty")
        if settings.taxii_collection_url: configured.append("taxii")
        for name in configured:
            statuses[name] = "dry-run (mock mode)"

    if not statuses:
        statuses["noop"] = "no destinations configured"

    log.info("dispatched", alert_id=alert.id, statuses=statuses)
    return statuses


def _format(result) -> str:
    """Compact status string from a DeliveryResult."""
    if result.success:
        return f"ok ({result.http_status})"
    if result.http_status:
        return f"fail ({result.http_status}): {result.error or ''}"[:120]
    return f"error: {result.error or 'unknown'}"[:120]


def _post_generic(url: str, payload: dict, signing_secret: str, *, dry: bool) -> str:
    """POST to a generic webhook with optional HMAC-SHA256 signature."""
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json"}
    if signing_secret:
        sig = hmac.new(signing_secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-DoppelDomain-Signature"] = f"sha256={sig}"
        headers["X-DoppelDomain-Schema"] = payload.get("schema", "")
    if dry:
        log.info("webhook.generic.dry", url=url, signed=bool(signing_secret), size=len(body))
        return "dry-run"
    try:
        r = httpx.post(url, content=body, headers=headers, timeout=10)
        return f"{r.status_code}"
    except Exception as exc:  # noqa: BLE001
        return f"error:{exc}"


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
        # Enhanced signals (v0.2)
        "attack_family": verdict.attack_family,
        "attack_family_confidence": verdict.attack_family_confidence,
        "kit_match": verdict.kit_match,
        "kit_match_confidence": verdict.kit_match_confidence,
        "cloaking_detected": verdict.cloaking_detected,
        "cloaking_evidence": verdict.cloaking_evidence,
        "created_at": alert.created_at.isoformat(),
    }


def _post_slack(url: str, payload: dict, *, dry: bool) -> str:
    # Surface the new signals in the Slack post so the SOC sees them at a glance
    signal_lines = []
    if payload.get("attack_family"):
        signal_lines.append(f"_Family:_ *{payload['attack_family']}*")
    if payload.get("kit_match"):
        signal_lines.append(f"_Kit:_ *{payload['kit_match']}*")
    if payload.get("cloaking_detected"):
        signal_lines.append("_Geo-cloaking:_ *DETECTED*")
    signals_block = ("  ·  ".join(signal_lines)) if signal_lines else "_No structured signals_"

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
                        f"_ASN:_ {payload['asn'] or '?'}\n"
                        f"{signals_block}"
                    ),
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Evidence*\n" + "\n".join(f"• {e}" for e in payload["evidence_summary"][:5])},
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
