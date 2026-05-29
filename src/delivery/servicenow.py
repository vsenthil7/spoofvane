"""
ServiceNow ITSM integration.

DoppelDomain alerts are pushed as ServiceNow incidents so SOC/IR teams can
manage them inside their existing workflow. Bidirectional sync is intended
but not implemented here — when an analyst closes the incident in
ServiceNow, a webhook (configured in ServiceNow Business Rules) should call
``POST /api/alerts/{id}/triage`` back to DoppelDomain. The route already
records that as feedback.

Configuration (in settings.py):

* ``servicenow_instance`` — e.g. ``acme.service-now.com``
* ``servicenow_user``     — basic-auth user with itil role
* ``servicenow_pass``     — that user's password (use Vault in production)

Calling ``send_alert_as_incident()`` is no-op-with-warning if the integration
isn't configured, so the pipeline doesn't fail just because the customer
hasn't connected ServiceNow yet.
"""

from __future__ import annotations

import base64

from ..common.logging import get_logger
from ..common.models import Alert, Brand, InspectionResult, VerdictResult
from ..common.settings import get_settings
from .integration_base import DeliveryResult, post_with_retry, severity_to_servicenow

logger = get_logger(__name__)


def send_alert_as_incident(
    alert: Alert,
    brand: Brand,
    inspection: InspectionResult,
    verdict: VerdictResult,
) -> DeliveryResult | None:
    """Create a ServiceNow incident for ``alert``. Returns None if not configured."""
    settings = get_settings()
    if not (
        settings.servicenow_instance
        and settings.servicenow_user
        and settings.servicenow_pass
    ):
        return None

    url = f"https://{settings.servicenow_instance}/api/now/table/incident"

    description_lines = [
        f"Brand: {brand.name}",
        f"Suspect URL: {alert.suspect_url}",
        f"Verdict: {verdict.verdict.value} (confidence {verdict.confidence:.0%})",
        f"Composite score: see DoppelDomain alert {alert.id}",
        "",
        "Evidence:",
    ]
    description_lines.extend(f"  - {line}" for line in verdict.evidence_summary[:8])
    if verdict.attack_family:
        description_lines.append(f"Attack family: {verdict.attack_family}")
    if verdict.kit_match:
        description_lines.append(
            f"Phishing kit fingerprint: {verdict.kit_match} "
            f"({(verdict.kit_match_confidence or 0):.0%} confidence)"
        )
    if verdict.cloaking_detected:
        description_lines.append("Geo-cloaking detected — see evidence panel.")

    body = {
        "short_description": (
            f"[DoppelDomain] {alert.severity.value.upper()} — "
            f"{brand.name} impersonation: {alert.suspect_url[:80]}"
        ),
        "description": "\n".join(description_lines),
        "category": "Security",
        "subcategory": "Phishing",
        "impact": severity_to_servicenow(alert.severity.value),
        "urgency": severity_to_servicenow(alert.severity.value),
        "correlation_id": alert.id,  # so updates can find the right ticket
        "u_doppeldomain_alert_id": alert.id,  # custom field convention
        "u_doppeldomain_evidence_pdf": (
            f"https://{settings.servicenow_instance}-doppeldomain/api/alerts/"
            f"{alert.id}/evidence.pdf"
        ),
    }

    creds = f"{settings.servicenow_user}:{settings.servicenow_pass}"
    auth = base64.b64encode(creds.encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}

    return post_with_retry(
        integration="servicenow",
        url=url,
        body=body,
        headers=headers,
        signing_secret=None,  # ServiceNow uses basic auth, not HMAC signing
    )
