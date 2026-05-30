"""v07 W13 — Expanded delivery / integration channels.

Existing integrations: ServiceNow, Sentinel, PagerDuty, Cortex XSOAR, TAXII,
webhooks, MCP. This package adds the channels competitors ship that we lacked:
Splunk HEC, CrowdStrike Falcon, Slack app, Microsoft Teams, Jira cases, Okta
event hook, and a STIX 2.1 bundle exporter.

Each channel is a PURE deterministic formatter: it maps a normalized
DeliveryFinding into the vendor's exact payload schema. Network delivery reuses
integration_base.post_with_retry and is 🔒 BLOCKED-ENV without credentials; the
formatters are fully unit-testable offline (distinct findings => distinct
payloads; severity maps correctly per vendor).
"""
from __future__ import annotations

from .common import DeliveryFinding
from .splunk_hec import format_splunk_hec
from .crowdstrike_falcon import format_falcon_ioc
from .slack_app import format_slack_message
from .teams_app import format_teams_card
from .jira_cases import format_jira_issue
from .okta_eventhook import format_okta_event
from .stix_bundle import build_stix_bundle

__all__ = [
    "DeliveryFinding", "format_splunk_hec", "format_falcon_ioc",
    "format_slack_message", "format_teams_card", "format_jira_issue",
    "format_okta_event", "build_stix_bundle",
]
