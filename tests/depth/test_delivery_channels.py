"""v07 W13 Gate — expanded delivery channels differential probe.

Each channel formatter maps a finding into the vendor's exact schema. Distinct
findings => distinct payloads; severity maps correctly per vendor; STIX bundle is
deterministic and links campaigns; Okta event is report-only (never locks).
Network delivery 🔒 BLOCKED-ENV (formatters are pure/offline).
"""
from __future__ import annotations

from src.delivery.channels.common import DeliveryFinding
from src.delivery.channels.splunk_hec import format_splunk_hec
from src.delivery.channels.crowdstrike_falcon import format_falcon_ioc
from src.delivery.channels.slack_app import format_slack_message
from src.delivery.channels.teams_app import format_teams_card
from src.delivery.channels.jira_cases import format_jira_issue
from src.delivery.channels.okta_eventhook import format_okta_event
from src.delivery.channels.stix_bundle import build_stix_bundle


def _finding(**kw) -> DeliveryFinding:
    base = dict(finding_id="f1", brand="AcmeBank",
                suspect_url="https://acme-login.top/signin", verdict="malicious",
                severity="critical", surface="domain", ioc_type="domain",
                ioc_value="acme-login.top", confidence=0.92)
    base.update(kw)
    return DeliveryFinding(**base)


def test_splunk_hec_envelope_and_urgency():
    crit = format_splunk_hec(_finding(severity="critical"))
    low = format_splunk_hec(_finding(severity="low"))
    assert crit["event"]["urgency"] == "critical"
    assert low["event"]["urgency"] == "low"
    assert crit["sourcetype"] == "spoofvane:alert"
    assert crit["event"]["brand"] == "AcmeBank"


def test_falcon_maps_url_to_domain_and_severity():
    f = format_falcon_ioc(_finding(ioc_type="url", ioc_value="https://acme-login.top/x"))
    assert f["type"] == "domain"
    assert f["value"] == "acme-login.top"   # URL reduced to domain for Falcon
    assert f["severity"] == "critical"
    assert "spoofvane" in f["tags"]


def test_slack_and_teams_distinct_severity_colors():
    crit = format_slack_message(_finding(severity="critical"))
    low = format_slack_message(_finding(severity="low"))
    assert crit["attachments"][0]["color"] != low["attachments"][0]["color"]
    teams = format_teams_card(_finding(severity="critical"))
    assert teams["@type"] == "MessageCard"
    assert any(fact["name"] == "Verdict" for fact in teams["sections"][0]["facts"])


def test_jira_priority_by_severity():
    crit = format_jira_issue(_finding(severity="critical"))
    med = format_jira_issue(_finding(severity="medium"))
    assert crit["fields"]["priority"]["name"] == "Highest"
    assert med["fields"]["priority"]["name"] == "Medium"
    assert crit["fields"]["project"]["key"] == "SEC"


def test_okta_event_is_report_only():
    ev = format_okta_event(_finding(), target_user="jane@acmebank.com")
    assert ev["debugContext"]["debugData"]["reportOnly"] is True
    assert ev["target"][0]["id"] == "jane@acmebank.com"


def test_two_findings_distinct_payloads():
    a = format_splunk_hec(_finding(finding_id="f1", ioc_value="acme-login.top"))
    b = format_splunk_hec(_finding(finding_id="f2", ioc_value="acme-verify.xyz"))
    assert a["event"] != b["event"]


def test_stix_bundle_deterministic_and_links_campaign():
    findings = [_finding(finding_id="f1", ioc_value="acme-login.top", campaign_id="camp_1"),
                _finding(finding_id="f2", ioc_value="acme-verify.xyz", campaign_id="camp_1")]
    b1 = build_stix_bundle(findings)
    b2 = build_stix_bundle(findings)
    assert b1 == b2  # deterministic
    types = [o["type"] for o in b1["objects"]]
    assert "indicator" in types
    assert "campaign" in types
    assert "relationship" in types
    # Only one campaign object even though two indicators reference it.
    assert types.count("campaign") == 1


def test_stix_empty_bundle():
    b = build_stix_bundle([])
    assert b["type"] == "bundle"
    assert b["objects"] == []
