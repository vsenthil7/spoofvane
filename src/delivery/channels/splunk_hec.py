"""W13 Splunk HTTP Event Collector (HEC) formatter."""
from __future__ import annotations

from .common import DeliveryFinding, severity_to_splunk


def format_splunk_hec(finding: DeliveryFinding, sourcetype: str = "spoofvane:alert") -> dict:
    """Build a Splunk HEC event envelope. HEC expects {event, sourcetype,
    source, ...} with the payload under `event`."""
    return {
        "sourcetype": sourcetype,
        "source": "spoofvane",
        "event": {
            "finding_id": finding.finding_id,
            "brand": finding.brand,
            "suspect_url": finding.suspect_url,
            "verdict": finding.verdict,
            "urgency": severity_to_splunk(finding.severity),
            "surface": finding.surface,
            "ioc_type": finding.ioc_type,
            "ioc_value": finding.ioc_value,
            "confidence": finding.confidence,
            "campaign_id": finding.campaign_id,
        },
    }
