"""W13 Jira issue formatter (Jira Cloud REST v3 create-issue schema)."""
from __future__ import annotations

from .common import DeliveryFinding, severity_rank

# Jira priority names by severity.
_JIRA_PRIORITY = {"critical": "Highest", "high": "High", "medium": "Medium", "low": "Low"}


def format_jira_issue(finding: DeliveryFinding, project_key: str = "SEC",
                      issue_type: str = "Task") -> dict:
    """Build a Jira create-issue payload (fields envelope)."""
    return {
        "fields": {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "priority": {"name": _JIRA_PRIORITY.get(finding.severity, "Low")},
            "summary": f"[SpoofVane] {finding.verdict} {finding.surface} — {finding.brand}",
            "labels": ["spoofvane", finding.surface, f"sev-{finding.severity}"],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [
                        {"type": "text",
                         "text": f"IOC {finding.ioc_type}={finding.ioc_value}; "
                                 f"confidence {finding.confidence:.0%}; "
                                 f"finding {finding.finding_id}."}
                    ]},
                ],
            },
        }
    }
