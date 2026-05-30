"""W13 Slack app formatter (Block Kit message)."""
from __future__ import annotations

from .common import DeliveryFinding, severity_to_slack_color


def format_slack_message(finding: DeliveryFinding) -> dict:
    """Build a Slack Block Kit message with an attachment colored by severity."""
    return {
        "attachments": [
            {
                "color": severity_to_slack_color(finding.severity),
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text",
                                 "text": f"SpoofVane: {finding.severity.upper()} — {finding.brand}"},
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Verdict:*\n{finding.verdict}"},
                            {"type": "mrkdwn", "text": f"*Surface:*\n{finding.surface}"},
                            {"type": "mrkdwn", "text": f"*IOC:*\n`{finding.ioc_value}`"},
                            {"type": "mrkdwn", "text": f"*Confidence:*\n{finding.confidence:.0%}"},
                        ],
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {"type": "button",
                             "text": {"type": "plain_text", "text": "View in SpoofVane"},
                             "url": f"https://console.spoofvane.example/alerts/{finding.finding_id}"},
                        ],
                    },
                ],
            }
        ]
    }
