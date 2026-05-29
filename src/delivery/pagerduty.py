"""
PagerDuty integration.

For ``critical`` and ``high`` severity alerts we trigger PagerDuty incidents
on the customer's security on-call rotation. Triage in SpoofVane (or
ServiceNow → triage) closes the PagerDuty incident via the same Events API.

Configuration:

* ``pagerduty_routing_key`` — the integration's Routing Key (32 chars)
* ``pagerduty_service_url`` — endpoint URL (default
  https://events.pagerduty.com/v2/enqueue)

Each alert maps to one PagerDuty event with ``dedup_key=alert_id`` so
re-sends update rather than duplicate.
"""

from __future__ import annotations

from ..common.logging import get_logger
from ..common.models import Alert, Brand, InspectionResult, Severity, VerdictResult
from ..common.settings import get_settings
from .integration_base import DeliveryResult, post_with_retry, severity_to_pagerduty

logger = get_logger(__name__)


# Only page out for these severities. Customers tune via their own rotation
# but this is the default our integration ships with — paging on every medium
# alert is how SOC teams get fatigued.
_PAGE_SEVERITIES: set[Severity] = {Severity.CRITICAL, Severity.HIGH}


def trigger_pagerduty(
    alert: Alert,
    brand: Brand,
    inspection: InspectionResult,
    verdict: VerdictResult,
) -> DeliveryResult | None:
    settings = get_settings()
    if not settings.pagerduty_routing_key:
        return None
    if alert.severity not in _PAGE_SEVERITIES:
        logger.debug(
            "pagerduty.skipped_severity", alert_id=alert.id, severity=alert.severity.value
        )
        return None

    body = {
        "routing_key": settings.pagerduty_routing_key,
        "event_action": "trigger",
        "dedup_key": alert.id,
        "payload": {
            "summary": (
                f"[SpoofVane] {alert.severity.value.upper()} — "
                f"{brand.name} impersonation detected: {alert.suspect_url[:100]}"
            ),
            "severity": severity_to_pagerduty(alert.severity.value),
            "source": "spoofvane",
            "component": brand.name,
            "group": "brand-impersonation",
            "class": verdict.verdict.value,
            "custom_details": {
                "alert_id": alert.id,
                "brand_id": brand.id,
                "verdict": verdict.verdict.value,
                "confidence": verdict.confidence,
                "attack_family": verdict.attack_family,
                "kit_match": verdict.kit_match,
                "cloaking_detected": verdict.cloaking_detected,
                "evidence": verdict.evidence_summary[:5],
            },
        },
        "links": [
            {
                "href": f"https://spoofvane.example/alerts/{alert.id}",
                "text": "Inspect alert in SpoofVane",
            },
        ],
    }

    return post_with_retry(
        integration="pagerduty",
        url=settings.pagerduty_service_url,
        body=body,
    )


def resolve_pagerduty(alert_id: str) -> DeliveryResult | None:
    """Send a resolve event for a previously-triggered alert."""
    settings = get_settings()
    if not settings.pagerduty_routing_key:
        return None
    body = {
        "routing_key": settings.pagerduty_routing_key,
        "event_action": "resolve",
        "dedup_key": alert_id,
    }
    return post_with_retry(
        integration="pagerduty",
        url=settings.pagerduty_service_url,
        body=body,
    )
