"""v07 W11 Gate — email-auth differential probe.

A spoofing source IP failing SPF+DKIM flags; an aligned legitimate sender
passes; DMARC report parses + aggregates unauthorized senders; BIMI valid vs
invalid; lookalike cousin-domains detected. Live RUA ingestion 🔒 BLOCKED-ENV.
"""
from __future__ import annotations

from src.email_auth.base import DmarcReport
from src.email_auth.dmarc_monitor import analyze_dmarc
from src.email_auth.spf_dkim_checker import check_alignment
from src.email_auth.bimi_validator import validate_bimi
from src.email_auth.lookalike_sender_detector import detect_lookalike_senders

_DMARC_XML = """<?xml version="1.0"?>
<feedback>
  <report_metadata><org_name>google.com</org_name><report_id>rpt-123</report_id></report_metadata>
  <policy_published><domain>acmebank.com</domain><p>reject</p></policy_published>
  <record>
    <row><source_ip>203.0.113.10</source_ip><count>120</count>
      <policy_evaluated><disposition>none</disposition><dkim>pass</dkim><spf>pass</spf></policy_evaluated></row>
    <identifiers><header_from>acmebank.com</header_from></identifiers>
  </record>
  <record>
    <row><source_ip>198.51.100.66</source_ip><count>340</count>
      <policy_evaluated><disposition>reject</disposition><dkim>fail</dkim><spf>fail</spf></policy_evaluated></row>
    <identifiers><header_from>acmebank.com</header_from></identifiers>
  </record>
</feedback>"""


def test_spoofing_source_fails_legit_passes():
    spoof = check_alignment("198.51.100.66", "ceo@acmebank.com", spf_pass=False, dkim_pass=False)
    legit = check_alignment("203.0.113.10", "noreply@acmebank.com", spf_pass=True, dkim_pass=True)
    assert spoof.verdict == "fail" and spoof.spoof_risk == 1.0
    assert legit.verdict == "pass" and legit.spoof_risk == 0.0
    assert spoof.spoof_risk > legit.spoof_risk


def test_partial_alignment_mid_risk():
    partial = check_alignment("203.0.113.5", "x@acmebank.com", spf_pass=True, dkim_pass=False)
    assert partial.aligned is True  # SPF alone aligns
    full_fail = check_alignment("203.0.113.6", "y@acmebank.com", spf_pass=False, dkim_pass=False)
    assert full_fail.spoof_risk > partial.spoof_risk


def test_dmarc_report_parses_and_aggregates():
    report = DmarcReport.from_xml(_DMARC_XML)
    assert report.domain == "acmebank.com"
    a = analyze_dmarc(report)
    assert a.total_messages == 460
    assert a.passing_messages == 120
    assert a.failing_messages == 340
    assert "198.51.100.66" in a.unauthorized_source_ips
    assert a.spoofing_volume == 340
    assert 0.0 <= a.pass_rate <= 1.0


def test_bimi_valid_vs_invalid():
    valid = validate_bimi("acmebank.com", "reject",
                          "v=BIMI1; l=https://acmebank.com/logo.svg; a=https://acmebank.com/vmc.pem",
                          "https://acmebank.com/vmc.pem")
    invalid = validate_bimi("globex.com", "none", "v=BIMI1; l=https://globex.com/logo.svg", None)
    assert valid.valid is True and valid.reason == "valid"
    assert invalid.valid is False
    assert valid.logo_url and valid.logo_url.endswith("logo.svg")


def test_lookalike_senders_detected():
    found = detect_lookalike_senders("acmebank.com", [
        "acmebank.com",        # the real one, ignored
        "acmebank.net",        # tld swap
        "acmebamk.com",        # typo
        "acm3bank.com",        # homoglyph (e->3)
        "totally-unrelated.com",
    ])
    domains = {f.sender_domain for f in found}
    assert "acmebank.com" not in domains
    assert "acmebank.net" in domains
    assert "totally-unrelated.com" not in domains
    # Ranked by risk, highest first.
    risks = [f.risk for f in found]
    assert risks == sorted(risks, reverse=True)


def test_negative_no_lookalikes():
    assert detect_lookalike_senders("acmebank.com", ["microsoft.com", "google.com"]) == []
