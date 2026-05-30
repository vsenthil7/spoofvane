"""v07 W14 Gate — compliance & governance differential probe.

EU AI Act tiers differ by use-case; NIST GenAI coverage computed; evidence
records form a verifiable hash chain that breaks on tamper/reorder; regulatory
deadlines differ by regime; DPA validates lawful basis. All deterministic/offline.
"""
from __future__ import annotations

import pytest

from src.compliance.eu_ai_act import classify_ai_system, EuAiActClass
from src.compliance.nist_genai_profile import map_nist_controls, coverage_summary, NistControlStatus
from src.compliance.evidence_provenance import build_evidence_record, verify_chain
from src.compliance.regulatory_reporter import build_breach_report
from src.compliance.dpa_gdpr import build_dpa_record


def test_eu_ai_act_tiers_differ():
    high = classify_ai_system("fraud_screening", affects_individuals=True, automated_decisions=True)
    limited = classify_ai_system("report_drafting", generates_content=True)
    minimal = classify_ai_system("log_aggregation")
    prohibited = classify_ai_system("social_scoring")
    assert high.risk_class == EuAiActClass.HIGH_RISK
    assert limited.risk_class == EuAiActClass.LIMITED_RISK
    assert minimal.risk_class == EuAiActClass.MINIMAL_RISK
    assert prohibited.risk_class == EuAiActClass.PROHIBITED
    assert "human_oversight" in high.obligations
    assert high.obligations != limited.obligations


def test_nist_coverage_summary():
    controls = map_nist_controls()
    assert len(controls) >= 6
    summary = coverage_summary()
    assert summary["total"] == len(controls)
    assert 0 <= summary["coverage_pct"] <= 100
    assert summary["implemented"] >= 1


def test_evidence_chain_verifies_and_tamper_breaks():
    r1 = build_evidence_record("f1", "2026-05-30T00:00:00Z", b"screenshot-bytes-1")
    r2 = build_evidence_record("f2", "2026-05-30T00:01:00Z", b"screenshot-bytes-2",
                               prev_hash=r1.record_hash)
    r3 = build_evidence_record("f3", "2026-05-30T00:02:00Z", b"screenshot-bytes-3",
                               prev_hash=r2.record_hash)
    assert verify_chain([r1, r2, r3]) is True
    # Reorder breaks the chain.
    assert verify_chain([r1, r3, r2]) is False
    # Content tamper breaks it (record_hash no longer matches).
    r2.content_sha256 = "deadbeef"
    assert verify_chain([r1, r2, r3]) is False


def test_evidence_record_links_c2pa():
    r = build_evidence_record("f1", "2026-05-30T00:00:00Z", "x", c2pa_trust="trusted")
    assert r.c2pa_trust == "trusted"
    assert r.verify_link("0" * 64) is True


def test_regulatory_deadlines_differ_by_regime():
    gdpr = build_breach_report("gdpr", "inc1", "2026-05-30T00:00:00Z", 5000, involves_personal_data=True)
    dora = build_breach_report("dora", "inc1", "2026-05-30T00:00:00Z", 5000, involves_personal_data=False)
    assert gdpr.hours_to_deadline == 72
    assert dora.hours_to_deadline == 4
    assert gdpr.notifiable is True
    assert gdpr.required_fields != dora.required_fields
    with pytest.raises(ValueError):
        build_breach_report("unknown", "inc1", "2026-05-30T00:00:00Z", 1, False)


def test_gdpr_not_notifiable_without_personal_data():
    r = build_breach_report("gdpr", "inc2", "2026-05-30T00:00:00Z", 100, involves_personal_data=False)
    assert r.notifiable is False


def test_dpa_validates_lawful_basis_and_minimization():
    ok = build_dpa_record("brand_monitoring", "legitimate_interest",
                          ["hashed_fingerprint", "public_domain_data"], retention_days=365)
    assert ok.minimization_applied is True
    assert ok.safeguards == []  # no cross-border
    xborder = build_dpa_record("intel_sharing", "legitimate_interest",
                               ["redacted_credential"], retention_days=90, cross_border=True)
    assert "standard_contractual_clauses" in xborder.safeguards
    with pytest.raises(ValueError):
        build_dpa_record("x", "not_a_basis", ["y"], 30)


def test_dpa_minimization_flag_on_raw_data():
    rec = build_dpa_record("x", "consent", ["raw_credential"], retention_days=10)
    assert rec.minimization_applied is False  # raw_ prefix => minimization not applied
