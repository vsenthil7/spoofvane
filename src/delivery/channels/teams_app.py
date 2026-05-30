"""W13 Microsoft Teams formatter (Adaptive Card via connector webhook)."""
from __future__ import annotations

from .common import DeliveryFinding, severity_to_slack_color


def format_teams_card(finding: DeliveryFinding) -> dict:
    """Build a Teams MessageCard (Office 365 connector schema)."""
    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": severity_to_slack_color(finding.severity).lstrip("#"),
        "summary": f"SpoofVane {finding.severity} alert for {finding.brand}",
        "sections": [
            {
                "activityTitle": f"SpoofVane: {finding.severity.upper()} — {finding.brand}",
                "facts": [
                    {"name": "Verdict", "value": finding.verdict},
                    {"name": "Surface", "value": finding.surface},
                    {"name": "IOC", "value": finding.ioc_value},
                    {"name": "Confidence", "value": f"{finding.confidence:.0%}"},
                ],
                "markdown": True,
            }
        ],
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "View in SpoofVane",
                "targets": [{"os": "default",
                             "uri": f"https://console.spoofvane.example/alerts/{finding.finding_id}"}],
            }
        ],
    }
