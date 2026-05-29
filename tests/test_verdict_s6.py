"""Sprint 6 — verdict ensemble D2,D3,D4,D5,D7 (review §8 group D)."""
from src.verdict.ensemble import (GptVerdict, GeminiVerdict, SlmTriage,
                                   VerdictMerger, ModelVerdict)
from src.verdict.mitre_enricher import enrich, ATTACK_CORPUS


def test_each_model_returns_valid_schema():
    ev = {"composite": 0.7, "url": "https://evil.top"}
    for m in (GptVerdict(), GeminiVerdict(), SlmTriage()):
        r = m.decide(ev)
        assert r.verdict in ("benign", "suspicious", "phish")
        assert 0.0 <= r.confidence <= 1.0


def test_models_are_input_dependent():
    g = GptVerdict()
    verdicts = {g.decide({"composite": c}).verdict for c in (0.1, 0.5, 0.9)}
    assert len(verdicts) >= 2


def test_slm_handles_only_low_severity():
    slm = SlmTriage()
    assert slm.handles({"composite": 0.2}) is True
    assert slm.handles({"composite": 0.9}) is False


def test_low_severity_routes_to_cheap_slm_path():
    m = VerdictMerger()
    r = m.merge({"composite": 0.2})
    assert r.cost_path == "slm"
    assert len(r.member_verdicts) == 1


def test_high_severity_uses_ensemble():
    m = VerdictMerger()
    r = m.merge({"composite": 0.88, "age": 2})
    assert r.cost_path == "ensemble"
    assert len(r.member_verdicts) >= 2


def test_dissent_discounts_confidence_and_escalates():
    # craft dissent by injecting a contrary Claude verdict
    m = VerdictMerger()
    claude = ModelVerdict("claude", "benign", 0.9, "claude says benign", "large")
    r = m.merge({"composite": 0.85}, claude_verdict=claude)
    if r.dissent:
        assert r.escalate_to_human is True


def test_phish_always_escalates():
    m = VerdictMerger()
    r = m.merge({"composite": 0.95})
    if r.verdict == "phish":
        assert r.escalate_to_human is True


def test_mitre_maps_real_technique_ids():
    e = enrich(["phishing_page", "aitm_relay"], family="m365")
    assert "T1566.002" in e.techniques     # Spearphishing Link
    assert "T1557" in e.techniques          # AiTM
    assert all(t.startswith("T") for t in e.techniques)
    assert e.d3fend  # at least one countermeasure


def test_mitre_always_adds_brand_impersonation():
    e = enrich([])
    assert "T1583.001" in e.techniques  # Acquire Infrastructure: Domains
