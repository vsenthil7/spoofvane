"""Sprint 10 — AI surfaces H2,H3,H5,H7,H8,H9,H10 (review §8 group H)."""
from src.ai_surfaces.surfaces import (AuditNlSearch, BrandWizard, ExecAttackSurface,
                                       IntelNarrator, KitExplainer, TakedownDrafter, TtpProposer)


AUDIT = [
    {"actor_role": "analyst", "tenant_id": "acme", "action": "takedown_submit", "outcome": "ok"},
    {"actor_role": "admin", "tenant_id": "acme", "action": "login", "outcome": "ok"},
    {"actor_role": "analyst", "tenant_id": "beta", "action": "review", "outcome": "denied"},
]


def test_h2_nl_search_parses_filters():
    r = AuditNlSearch().search("analyst takedown actions for tenant acme", AUDIT)
    assert r.interpreted_filters["actor_role"] == "analyst"
    assert r.interpreted_filters["action_contains"] == "takedown"
    assert len(r.matched) == 1


def test_h2_denied_filter():
    r = AuditNlSearch().search("denied actions", AUDIT)
    assert all(row["outcome"] == "denied" for row in r.matched)


def test_h3_brand_wizard_keywords_input_dependent():
    a = BrandWizard().plan("Acme Bank", "https://acme.com/login")
    b = BrandWizard().plan("Globex Corp", "https://globex.com/login")
    assert a.suggested_keywords != b.suggested_keywords
    assert "acmebank" in a.suggested_keywords


def test_h5_exec_surface_input_dependent_and_handles():
    a = ExecAttackSurface().scan("Jane CEO", ["x", "linkedin"])
    b = ExecAttackSurface().scan("John CFO", ["x", "linkedin"])
    assert a.impersonation_handles != b.impersonation_handles
    assert 0.0 <= a.risk <= 1.0


def test_h7_narrator_reflects_verdict():
    phish = IntelNarrator().narrate({"verdict": "phish", "url": "https://e.top"})
    benign = IntelNarrator().narrate({"verdict": "benign", "url": "https://e.top"})
    assert "PHISH" in phish and "takedown" in phish
    assert "dismiss" in benign


def test_h8_kit_explainer_kb_hit_and_miss():
    hit = KitExplainer().explain("EvilProxy")
    miss = KitExplainer().explain("NeverSeenKit")
    assert hit.found_in_kb and "AiTM" in hit.explanation
    assert not miss.found_in_kb


def test_h9_takedown_drafter_requires_approval():
    d = TakedownDrafter().draft({"url": "https://e.top", "registrar": "nc", "brand": "Acme"})
    assert d["requires_human_approval"] is True
    assert "e.top" in d["subject"]


def test_h10_ttp_proposer_returns_real_techniques():
    p = TtpProposer().propose({"family": "m365", "capabilities": ["aitm_relay"]})
    assert p["primary_technique"].startswith("T")
    assert "T1557" in p["suggested_techniques"]  # AiTM
    assert p["d3fend_countermeasures"]
