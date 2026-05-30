"""W13 Okta event-hook formatter (Okta event-hook response schema).

When a validated credential exposure (W5) maps to an Okta-managed identity, this
emits an Okta system-log-compatible event so SOC workflows can react. It does
NOT lock accounts (that stays the W5 admin-gated action) — it only reports.
"""
from __future__ import annotations

from .common import DeliveryFinding


def format_okta_event(finding: DeliveryFinding, target_user: str | None = None) -> dict:
    """Build an Okta-event-hook-style event object (report-only)."""
    return {
        "eventType": "spoofvane.security.exposure",
        "version": "0",
        "severity": finding.severity.upper(),
        "displayMessage": f"SpoofVane {finding.surface} {finding.verdict} for {finding.brand}",
        "actor": {"id": "spoofvane", "type": "Service"},
        "target": [
            {"id": target_user or finding.ioc_value, "type": "User"
             if target_user else "Indicator"},
        ],
        "debugContext": {
            "debugData": {
                "findingId": finding.finding_id,
                "iocType": finding.ioc_type,
                "iocValue": finding.ioc_value,
                "confidence": finding.confidence,
                "reportOnly": True,     # never locks; W5 admin path does that
            }
        },
    }
