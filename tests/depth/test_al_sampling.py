"""v07 D3 Gate — active-learning sample-selection differential probe.

Uncertain findings (p near 0.5) are chosen over confident ones (p near 0/1);
diversify spreads the budget across surfaces while no-diversify clusters on the
noisiest surface; budget is respected; distinct batches yield distinct picks.
Pure/offline.
"""
from __future__ import annotations

from src.scoring.al_sampling import ScoredFinding, select_for_review


def _batch():
    return [
        ScoredFinding("d1", "domain", 0.50),      # max uncertainty
        ScoredFinding("d2", "domain", 0.52),
        ScoredFinding("d3", "domain", 0.55),
        ScoredFinding("s1", "social", 0.49),       # uncertain, other surface
        ScoredFinding("a1", "appstore", 0.97),     # confident -> low priority
        ScoredFinding("a2", "appstore", 0.02),     # confident -> low priority
    ]


def test_uncertain_chosen_over_confident():
    sel = select_for_review(_batch(), budget=3, diversify=False)
    ids = {f.finding_id for f in sel.selected}
    # The near-0.5 findings must be selected; the 0.97/0.02 ones must not (budget 3).
    assert "a1" not in ids and "a2" not in ids
    # Every selected finding is more uncertain than the rejected confident ones.
    chosen_unc = [1.0 - abs(f.probability - 0.5) * 2 for f in sel.selected]
    assert min(chosen_unc) >= 0.8


def test_diversify_spreads_across_surfaces():
    # Many uncertain domain findings + one uncertain social finding.
    findings = [ScoredFinding(f"d{i}", "domain", 0.50) for i in range(5)]
    findings.append(ScoredFinding("s1", "social", 0.50))
    div = select_for_review(findings, budget=2, diversify=True)
    nodiv = select_for_review(findings, budget=2, diversify=False)
    # Diversified picks one from each surface; non-diversified takes 2 domains.
    assert set(div.by_surface) == {"domain", "social"}
    assert nodiv.by_surface.get("domain") == 2


def test_budget_respected():
    sel = select_for_review(_batch(), budget=2)
    assert len(sel.selected) == 2
    assert sel.skipped == 4


def test_zero_budget_and_empty():
    assert select_for_review(_batch(), budget=0).selected == []
    assert select_for_review([], budget=5).selected == []


def test_distinct_batches_distinct_selection():
    a = select_for_review(_batch(), budget=2)
    b = select_for_review([ScoredFinding("x1", "darkweb", 0.5),
                           ScoredFinding("x2", "easm", 0.5)], budget=2)
    assert {f.finding_id for f in a.selected} != {f.finding_id for f in b.selected}


def test_all_confident_still_returns_least_confident():
    findings = [ScoredFinding("c1", "domain", 0.95), ScoredFinding("c2", "domain", 0.99)]
    sel = select_for_review(findings, budget=1)
    # Of two confident ones, the less-confident (0.95, closer to boundary) wins.
    assert sel.selected[0].finding_id == "c1"
