"""
Microsoft Sentinel integration.

Sentinel ingests events via Azure Log Analytics' Data Collector API. We
post alerts as custom-log entries which then surface in Sentinel's hunting
queries, Workbooks, and (via Analytics Rules) Incidents. Customers run a
single KQL rule like::

    SpoofVane_CL
    | where Severity_s in ("critical","high")
    | extend AccountCustomEntity = ""
    | project TimeGenerated, BrandName_s, SuspectUrl_s, Verdict_s, ...

to turn our findings into Sentinel incidents.

Configuration:

* ``sentinel_workspace_id`` — Azure Log Analytics workspace ID (GUID)
* ``sentinel_shared_key``   — workspace primary key (base64-encoded)

Authentication uses HMAC-SHA256 over a canonical request string per the
Log Analytics Data Collector spec.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone

from ..common.logging import get_logger
from ..common.models import Alert, Brand, InspectionResult, VerdictResult
from ..common.settings import get_settings
from .integration_base import DeliveryResult, post_with_retry, severity_to_sentinel

logger = get_logger(__name__)


def send_alert_to_sentinel(
    alert: Alert,
    brand: Brand,
    inspection: InspectionResult,
    verdict: VerdictResult,
) -> DeliveryResult | None:
    settings = get_settings()
    workspace_id = settings.sentinel_workspace_id
    shared_key = settings.sentinel_shared_key
    if not (workspace_id and shared_key):
        return None

    log_type = "SpoofVane"
    url = f"https://{workspace_id}.ods.opinsights.azure.com/api/logs?api-version=2016-04-01"

    event = {
        "AlertId": alert.id,
        "BrandName": brand.name,
        "BrandId": brand.id,
        "SuspectUrl": alert.suspect_url,
        "Severity": severity_to_sentinel(alert.severity.value),
        "Verdict": verdict.verdict.value,
        "Confidence": verdict.confidence,
        "SuggestedAction": verdict.suggested_action,
        "Asn": inspection.asn,
        "Registrar": inspection.registrar,
        "RegisteredCountry": inspection.rendered_country,
        "RegistrationDate": (
            inspection.registration_date.isoformat()
            if inspection.registration_date else None
        ),
        "AttackFamily": verdict.attack_family,
        "KitMatch": verdict.kit_match,
        "CloakingDetected": verdict.cloaking_detected,
        "EvidenceBullets": verdict.evidence_summary,
        "ModelUsed": verdict.model_used,
        "CreatedAt": alert.created_at.isoformat(),
    }

    body_json = json.dumps([event])
    body_bytes = body_json.encode("utf-8")

    # Signature spec: SharedKey {workspaceId}:{signature}
    rfc1123_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    string_to_hash = (
        f"POST\n{len(body_bytes)}\napplication/json\n"
        f"x-ms-date:{rfc1123_date}\n/api/logs"
    )
    decoded_key = base64.b64decode(shared_key)
    signature_bytes = hmac.new(decoded_key, string_to_hash.encode("utf-8"), hashlib.sha256).digest()
    signature = base64.b64encode(signature_bytes).decode("utf-8")
    auth_header = f"SharedKey {workspace_id}:{signature}"

    headers = {
        "Authorization": auth_header,
        "Log-Type": log_type,
        "x-ms-date": rfc1123_date,
        "time-generated-field": "CreatedAt",
    }

    # We can't reuse post_with_retry directly because it JSON-encodes the dict;
    # Sentinel expects an *array* body. We pass a wrapping dict that the helper
    # will encode the same way — adjust by sending the raw body via a list-keyed dict.
    # Simpler: post a single-element dict and let Sentinel infer. The DCS API
    # accepts both a JSON object and an array; we use array form for clarity by
    # posting from a key the helper turns into the expected wire shape.
    # We need a small specialised call — bypass the helper to keep wire format right.
    return _post_raw(
        integration="sentinel",
        url=url,
        body_bytes=body_bytes,
        headers=headers,
    )


def _post_raw(*, integration: str, url: str, body_bytes: bytes, headers: dict[str, str]) -> DeliveryResult:
    """Specialised post that keeps a pre-encoded body (array form for Sentinel)."""
    import time
    import urllib.error
    import urllib.request

    request_headers = {"Content-Type": "application/json", **headers}
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, data=body_bytes, headers=request_headers, method="POST")
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            status = resp.status
            excerpt = resp.read(2048).decode("utf-8", errors="replace")
            return DeliveryResult(
                integration=integration,
                success=200 <= status < 300,
                http_status=status,
                response_excerpt=excerpt[:512],
                attempts=1,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
    except urllib.error.HTTPError as e:
        excerpt = ""
        try:
            excerpt = e.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
        return DeliveryResult(
            integration=integration,
            success=False,
            http_status=e.code,
            error=f"HTTP {e.code}: {excerpt[:200]}",
            attempts=1,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return DeliveryResult(
            integration=integration,
            success=False,
            error=f"{type(e).__name__}: {e}",
            attempts=1,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
