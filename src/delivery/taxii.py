"""
STIX 2.1 / TAXII 2.1 threat intel publishing.

SpoofVane alerts about brand impersonation infrastructure are valuable
threat intel for the wider security community. We translate alerts into
STIX 2.1 indicator bundles and POST them to a TAXII 2.1 collection. ISACs
and other security tools subscribe to that collection to ingest our IoCs.

A typical STIX bundle from one alert looks like::

    {
      "type": "bundle",
      "id": "bundle--<uuid>",
      "objects": [
        {"type": "indicator", "pattern": "[url:value = 'https://...']", ...},
        {"type": "malware", "name": "16Shop", ...},
        {"type": "relationship", "source_ref": "...", "target_ref": "..."}
      ]
    }

Configuration:

* ``taxii_collection_url`` — full URL of the target TAXII collection
* ``taxii_username``       — basic-auth username
* ``taxii_password``       — basic-auth password
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone
from typing import Any

from ..common.logging import get_logger
from ..common.models import Alert, Brand, InspectionResult, VerdictResult
from ..common.settings import get_settings
from .integration_base import DeliveryResult, post_with_retry

logger = get_logger(__name__)


def _stix_id(prefix: str) -> str:
    return f"{prefix}--{uuid.uuid4()}"


def _iso(dt: datetime | None) -> str:
    return (dt or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()


def build_stix_bundle(
    alert: Alert,
    brand: Brand,
    inspection: InspectionResult,
    verdict: VerdictResult,
) -> dict[str, Any]:
    """Return a STIX 2.1 bundle representing this alert."""
    now_iso = _iso(datetime.now(timezone.utc))
    observed_iso = _iso(alert.created_at)

    objects: list[dict[str, Any]] = []

    # Identity: us, the producer
    identity_id = _stix_id("identity")
    objects.append({
        "type": "identity",
        "spec_version": "2.1",
        "id": identity_id,
        "created": now_iso,
        "modified": now_iso,
        "name": "SpoofVane",
        "identity_class": "organization",
        "sectors": ["technology"],
        "description": "Brand-impersonation detection platform",
    })

    # Indicator: the suspect URL itself
    indicator_id = _stix_id("indicator")
    objects.append({
        "type": "indicator",
        "spec_version": "2.1",
        "id": indicator_id,
        "created": now_iso,
        "modified": now_iso,
        "created_by_ref": identity_id,
        "name": f"{brand.name} impersonation",
        "description": " | ".join(verdict.evidence_summary[:5]) or "Brand impersonation detected",
        "indicator_types": ["malicious-activity"],
        "pattern": f"[url:value = '{alert.suspect_url}']",
        "pattern_type": "stix",
        "pattern_version": "2.1",
        "valid_from": observed_iso,
        "confidence": int(round(verdict.confidence * 100)),
        "labels": _stix_labels(verdict),
    })

    # If we matched a known kit, emit a Malware object + relationship
    if verdict.kit_match:
        malware_id = _stix_id("malware")
        objects.append({
            "type": "malware",
            "spec_version": "2.1",
            "id": malware_id,
            "created": now_iso,
            "modified": now_iso,
            "created_by_ref": identity_id,
            "name": verdict.kit_match,
            "malware_types": ["phishkit"],
            "is_family": True,
            "labels": [verdict.kit_match.lower().replace(" ", "-")],
        })
        objects.append({
            "type": "relationship",
            "spec_version": "2.1",
            "id": _stix_id("relationship"),
            "created": now_iso,
            "modified": now_iso,
            "created_by_ref": identity_id,
            "relationship_type": "indicates",
            "source_ref": indicator_id,
            "target_ref": malware_id,
        })

    # Observed-data object for the URL + ASN + registrar (forensic context)
    if inspection.asn or inspection.registrar:
        objects.append({
            "type": "observed-data",
            "spec_version": "2.1",
            "id": _stix_id("observed-data"),
            "created": now_iso,
            "modified": now_iso,
            "created_by_ref": identity_id,
            "first_observed": observed_iso,
            "last_observed": observed_iso,
            "number_observed": 1,
            "object_refs": [],
            "x_spoofvane_asn": inspection.asn,
            "x_spoofvane_registrar": inspection.registrar,
            "x_spoofvane_rendered_country": inspection.rendered_country,
            "x_spoofvane_cloaking_detected": verdict.cloaking_detected,
        })

    return {
        "type": "bundle",
        "id": _stix_id("bundle"),
        "objects": objects,
    }


def _stix_labels(verdict: VerdictResult) -> list[str]:
    labels: list[str] = ["brand-impersonation"]
    if verdict.attack_family:
        labels.append(f"family:{verdict.attack_family}")
    if verdict.kit_match:
        labels.append(f"kit:{verdict.kit_match.lower().replace(' ', '-')}")
    if verdict.cloaking_detected:
        labels.append("geo-cloaking")
    return labels


def publish_to_taxii(
    alert: Alert,
    brand: Brand,
    inspection: InspectionResult,
    verdict: VerdictResult,
) -> DeliveryResult | None:
    settings = get_settings()
    if not settings.taxii_collection_url:
        return None

    bundle = build_stix_bundle(alert, brand, inspection, verdict)

    headers = {
        "Accept": "application/taxii+json;version=2.1",
        "Content-Type": "application/taxii+json;version=2.1",
    }
    if settings.taxii_username and settings.taxii_password:
        creds = f"{settings.taxii_username}:{settings.taxii_password}"
        headers["Authorization"] = (
            f"Basic {base64.b64encode(creds.encode()).decode()}"
        )

    # TAXII 2.1 wraps the STIX bundle in an envelope
    body = {"objects": bundle["objects"]}

    return post_with_retry(
        integration="taxii",
        url=settings.taxii_collection_url,
        body=body,
        headers=headers,
    )
