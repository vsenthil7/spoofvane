"""
Shared infrastructure for enterprise integrations.

Every integration (ServiceNow, Sentinel, PagerDuty, TAXII, plain webhooks)
needs:

1. A configured target — URL + auth — populated from Settings
2. A way to translate an Alert into the target's payload shape
3. Resilient delivery: retries with backoff, error capture, no fatal raises
4. Optional HMAC signing of the outbound body

This module provides those pieces so individual integrations only define the
payload transformation and endpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Callable

import urllib.error
import urllib.request

from ..common.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class DeliveryResult:
    """Outcome of an outbound integration call."""

    integration: str
    success: bool
    http_status: int | None = None
    error: str | None = None
    response_excerpt: str | None = None
    attempts: int = 0
    duration_ms: int = 0


def post_with_retry(
    *,
    integration: str,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
    signing_secret: str | None = None,
    max_attempts: int = 3,
    base_backoff_seconds: float = 0.5,
    timeout_seconds: float = 8.0,
) -> DeliveryResult:
    """POST a JSON body with retry-with-backoff.

    If ``signing_secret`` is provided, an ``X-DoppelDomain-Signature`` header
    is added with HMAC-SHA256(secret, body)::

        sha256=<hex digest>

    The receiver verifies it to confirm the message came from us untampered.
    """
    body_bytes = json.dumps(body).encode("utf-8")
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    if signing_secret:
        mac = hmac.new(signing_secret.encode("utf-8"), body_bytes, hashlib.sha256)
        request_headers["X-DoppelDomain-Signature"] = f"sha256={mac.hexdigest()}"

    start = time.monotonic()
    last_error: str | None = None
    last_status: int | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(
                url, data=body_bytes, headers=request_headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                status = resp.status
                excerpt = resp.read(2048).decode("utf-8", errors="replace")
                duration_ms = int((time.monotonic() - start) * 1000)
                if 200 <= status < 300:
                    return DeliveryResult(
                        integration=integration,
                        success=True,
                        http_status=status,
                        response_excerpt=excerpt[:512],
                        attempts=attempt,
                        duration_ms=duration_ms,
                    )
                last_status = status
                last_error = f"HTTP {status}: {excerpt[:200]}"
        except urllib.error.HTTPError as e:
            last_status = e.code
            try:
                excerpt = e.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                excerpt = ""
            last_error = f"HTTP {e.code}: {excerpt[:200]}"
            # 4xx (client errors) are not retryable except 408/429
            if 400 <= e.code < 500 and e.code not in (408, 429):
                break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_error = f"{type(e).__name__}: {e}"

        if attempt < max_attempts:
            sleep_for = base_backoff_seconds * (2 ** (attempt - 1))
            time.sleep(sleep_for)

    duration_ms = int((time.monotonic() - start) * 1000)
    logger.warning(
        "integration.delivery_failed",
        integration=integration,
        url=url,
        attempts=max_attempts,
        last_status=last_status,
        last_error=last_error,
    )
    return DeliveryResult(
        integration=integration,
        success=False,
        http_status=last_status,
        error=last_error,
        attempts=max_attempts,
        duration_ms=duration_ms,
    )


# --------------------------------------------------------------------------- #
# Severity normalisation across vendor schemas
# --------------------------------------------------------------------------- #


def severity_to_servicenow(severity: str) -> int:
    """ServiceNow uses 1=Critical, 2=High, 3=Moderate, 4=Low, 5=Planning."""
    return {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4,
    }.get(severity, 5)


def severity_to_sentinel(severity: str) -> str:
    """Microsoft Sentinel incidents: High / Medium / Low / Informational."""
    return {
        "critical": "High",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
    }.get(severity, "Informational")


def severity_to_pagerduty(severity: str) -> str:
    """PagerDuty Events API v2 supports: critical / error / warning / info."""
    return {
        "critical": "critical",
        "high": "error",
        "medium": "warning",
        "low": "info",
    }.get(severity, "info")
