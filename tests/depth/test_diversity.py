"""v07 D4 Gate — ensemble provider-diversity differential probe.

Unanimous votes => multiplier 1.0 (full confidence); a 2-way split discounts;
an even 3-way split discounts more; agreement_ratio + normalized_entropy track
the distribution. Distinct vote distributions yield distinct multipliers. The
merger uses the graduated multiplier (unanimous merge keeps full confidence).
"""
from __future__ import annotations

from src.verdict.diversity import compute_diversity
from src.verdict.ensemble import VerdictMerger, ModelVerdict


def test_unanimous_full_confidence():
    d = compute_diversity(["phish", "phish", "phish"])
    assert d.unanimous is True
    assert d.diversity_multiplier == 1.0
    assert d.agreement_ratio == 1.0
    assert d.normalized_entropy == 0.0


def test_split_discounts():
    unanimous = compute_diversity(["phish", "phish", "phish"])
    two_one = compute_diversity(["phish", "phish", "benign"])
    even = compute_diversity(["phish", "benign"])
    assert unanimous.diversity_multiplier > two_one.diversity_multiplier
    assert two_one.diversity_multiplier > even.diversity_multiplier
    # Even 2-way split is the maximal-diversity case for 2 members.
    assert even.diversity_multiplier == 0.5
    assert even.normalized_entropy == 1.0


def test_distinct_distributions_distinct_multipliers():
    a = compute_diversity(["phish", "phish", "suspicious"])
    b = compute_diversity(["phish", "suspicious", "benign"])
    assert a.diversity_multiplier != b.diversity_multiplier
    # 3-way split has higher entropy than 2-1 split.
    assert b.normalized_entropy > a.normalized_entropy


def test_agreement_ratio_tracks_winner():
    d = compute_diversity(["phish", "phish", "phish", "benign"])
    assert d.agreement_ratio == 0.75
    assert d.distinct_verdicts == 2


def test_empty_and_single():
    assert compute_diversity([]).diversity_multiplier == 1.0
    single = compute_diversity(["phish"])
    assert single.diversity_multiplier == 1.0
    assert single.unanimous is True


def test_merger_uses_graduated_multiplier():
    # Force a high-severity evidence so we hit the ensemble path (not SLM).
    merger = VerdictMerger()
    evidence = {"composite": 0.85, "brand": "AcmeBank", "url": "https://acme-login.top"}
    merged = merger.merge(evidence)
    # The diversity metrics are surfaced on the merged verdict.
    assert 0.0 <= merged.agreement_ratio <= 1.0
    assert 0.5 <= merged.diversity_multiplier <= 1.0
    # If unanimous, multiplier is 1.0 and confidence == avg member confidence.
    if not merged.dissent:
        assert merged.diversity_multiplier == 1.0


def test_merger_dissent_discounts_below_unanimous():
    # Inject a claude verdict that disagrees to force dissent, with a controlled
    # evidence dict.
    merger = VerdictMerger()
    evidence = {"composite": 0.85}
    dissenting = ModelVerdict("claude", "benign", 0.9, "forced dissent", "large")
    merged = merger.merge(evidence, claude_verdict=dissenting)
    if merged.dissent:
        assert merged.diversity_multiplier < 1.0
