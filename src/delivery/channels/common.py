"""W13 common: the normalized DeliveryFinding + cross-vendor severity maps."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DeliveryFinding:
    """Normalized finding handed to any delivery channel formatter."""
    finding_id: str
    brand: str
    suspect_url: str
    verdict: str                 # malicious | suspicious | benign
    severity: str                # critical | high | medium | low
    surface: str                 # domain | social | appstore | marketplace | ...
    ioc_type: str = "url"        # url | domain | ip | cert | social_handle
    ioc_value: str = ""
    first_seen: str = ""
    confidence: float = 0.0
    campaign_id: str | None = None

    def __post_init__(self) -> None:
        if not self.ioc_value:
            self.ioc_value = self.suspect_url


# Generic severity -> integer rank (shared by several vendors).
_SEV_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def severity_rank(severity: str) -> int:
    return _SEV_RANK.get(severity, 0)


def severity_to_splunk(severity: str) -> str:
    # Splunk notable-event urgency.
    return {"critical": "critical", "high": "high", "medium": "medium",
            "low": "low"}.get(severity, "informational")


def severity_to_slack_color(severity: str) -> str:
    return {"critical": "#B00020", "high": "#D93F0B", "medium": "#E0A800",
            "low": "#2EA44F"}.get(severity, "#6C757D")
