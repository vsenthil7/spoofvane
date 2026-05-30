"""W13 STIX 2.1 bundle exporter.

Maps SpoofVane findings into a STIX 2.1 bundle (indicator + observed-data +
optional relationship to a campaign), so customers can ingest into any
STIX/TAXII-compatible TIP. Deterministic IDs derived from finding content so the
same finding always produces the same bundle.
"""
from __future__ import annotations

import hashlib
import uuid

from .common import DeliveryFinding

# Deterministic namespace so identical findings -> identical STIX IDs.
_NS = uuid.UUID("5f1e2d3c-4b5a-6c7d-8e9f-000000000001")


def _det_id(prefix: str, *parts: str) -> str:
    name = "|".join(parts)
    return f"{prefix}--{uuid.uuid5(_NS, name)}"


def _stix_pattern(finding: DeliveryFinding) -> str:
    t = finding.ioc_type
    v = finding.ioc_value
    if t in ("url",):
        return f"[url:value = '{v}']"
    if t in ("domain",):
        return f"[domain-name:value = '{v}']"
    if t in ("ip",):
        return f"[ipv4-addr:value = '{v}']"
    if t in ("cert",):
        return f"[x509-certificate:hashes.'SHA-256' = '{v}']"
    return f"[url:value = '{v}']"


def build_stix_bundle(findings: list[DeliveryFinding]) -> dict:
    objects: list[dict] = []
    for f in findings:
        ind_id = _det_id("indicator", f.finding_id, f.ioc_value)
        objects.append({
            "type": "indicator",
            "spec_version": "2.1",
            "id": ind_id,
            "name": f"SpoofVane {f.surface} {f.verdict}: {f.brand}",
            "pattern": _stix_pattern(f),
            "pattern_type": "stix",
            "valid_from": f.first_seen or "2026-01-01T00:00:00Z",
            "labels": [f.verdict, f.surface],
            "confidence": int(round(f.confidence * 100)),
        })
        if f.campaign_id:
            camp_id = _det_id("campaign", f.campaign_id)
            if not any(o["id"] == camp_id for o in objects):
                objects.append({
                    "type": "campaign", "spec_version": "2.1",
                    "id": camp_id, "name": f.campaign_id,
                })
            objects.append({
                "type": "relationship", "spec_version": "2.1",
                "id": _det_id("relationship", ind_id, camp_id),
                "relationship_type": "indicates",
                "source_ref": ind_id, "target_ref": camp_id,
            })
    return {
        "type": "bundle",
        "id": f"bundle--{uuid.uuid5(_NS, '|'.join(o['id'] for o in objects))}"
              if objects else f"bundle--{uuid.uuid5(_NS, 'empty')}",
        "objects": objects,
    }
