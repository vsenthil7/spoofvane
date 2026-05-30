"""v07 D3 — active-learning sample selection across all surfaces.

active_learning.py turns captured feedback into tuning recommendations. D3 adds
the OTHER half of the loop: given a batch of scored findings from EVERY surface
(domain/social/appstore/marketplace/darkweb/credleak/easm/rtp/deepfake), pick the
most informative ones to send to human review under a fixed review budget.

Two classic active-learning strategies, combined:
* uncertainty   — findings whose probability sits near the decision boundary
                  (0.5) are the most informative to label.
* diversity     — spread the budget across surfaces so review effort isn't spent
                  entirely on the single noisiest surface (round-robin by surface
                  over the uncertainty-ranked queue).

Pure function over scored items => fully offline-testable. Distinct batches yield
distinct selections; a confident item is never chosen over an uncertain one
within the same surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScoredFinding:
    finding_id: str
    surface: str
    probability: float       # calibrated P(malicious) in 0..1


@dataclass
class ReviewSelection:
    selected: list[ScoredFinding]
    by_surface: dict[str, int]
    skipped: int


def _uncertainty(p: float) -> float:
    """Distance-to-boundary uncertainty: max at p=0.5, min at 0/1."""
    return 1.0 - abs(p - 0.5) * 2.0


def select_for_review(findings: list[ScoredFinding], budget: int,
                      diversify: bool = True) -> ReviewSelection:
    """Pick up to `budget` most-informative findings for human labeling.

    With diversify=True, the budget is spread across surfaces round-robin over
    each surface's uncertainty-ranked queue, so no single surface monopolizes
    the review budget. With diversify=False, it's pure global uncertainty.
    """
    if budget <= 0 or not findings:
        return ReviewSelection([], {}, len(findings))

    # Rank every finding by uncertainty (most uncertain first), stable by id.
    ranked = sorted(findings, key=lambda f: (-_uncertainty(f.probability), f.finding_id))

    if not diversify:
        chosen = ranked[:budget]
    else:
        # Bucket the ranked findings per surface (preserves uncertainty order).
        per_surface: dict[str, list[ScoredFinding]] = {}
        for f in ranked:
            per_surface.setdefault(f.surface, []).append(f)
        chosen: list[ScoredFinding] = []
        # Round-robin across surfaces (surfaces ordered by their most-uncertain head).
        surface_order = sorted(per_surface,
                               key=lambda s: (-_uncertainty(per_surface[s][0].probability), s))
        idx = {s: 0 for s in per_surface}
        while len(chosen) < budget:
            progressed = False
            for s in surface_order:
                if len(chosen) >= budget:
                    break
                i = idx[s]
                if i < len(per_surface[s]):
                    chosen.append(per_surface[s][i])
                    idx[s] += 1
                    progressed = True
            if not progressed:
                break

    by_surface: dict[str, int] = {}
    for f in chosen:
        by_surface[f.surface] = by_surface.get(f.surface, 0) + 1
    return ReviewSelection(selected=chosen, by_surface=by_surface,
                           skipped=len(findings) - len(chosen))
