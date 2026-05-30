"""v07 D4 — ensemble provider-diversity metric.

The ensemble (ensemble.py) already does a disagreement-aware merge, but dissent
is a flat boolean discount (0.7x). D4 quantifies provider diversity so the
confidence discount scales with HOW MUCH the providers disagree:

* agreement_ratio — fraction of members voting for the winning verdict.
* normalized_entropy — Shannon entropy of the vote distribution / log2(k),
  0 (unanimous) .. 1 (maximally split).
* diversity_multiplier — maps agreement to a confidence multiplier in [0.5,1.0]:
  unanimous -> 1.0, evenly split -> ~0.5.

Pure functions over a list of verdict strings => fully offline-testable.
Distinct vote distributions yield distinct multipliers.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass


@dataclass
class DiversityMetrics:
    n_members: int
    distinct_verdicts: int
    agreement_ratio: float
    normalized_entropy: float
    diversity_multiplier: float
    unanimous: bool


def compute_diversity(votes: list[str]) -> DiversityMetrics:
    """Quantify how diverse a set of provider votes is."""
    n = len(votes)
    if n == 0:
        return DiversityMetrics(0, 0, 1.0, 0.0, 1.0, True)
    counts = Counter(votes)
    top = max(counts.values())
    agreement = top / n
    distinct = len(counts)

    # Normalized Shannon entropy over the vote distribution.
    if distinct <= 1:
        norm_entropy = 0.0
    else:
        entropy = -sum((c / n) * math.log2(c / n) for c in counts.values())
        norm_entropy = entropy / math.log2(distinct)

    # Confidence multiplier: 1.0 when unanimous, scaling down to 0.5 as
    # agreement falls toward 1/n. Linear in agreement_ratio over [1/n, 1].
    if n == 1:
        mult = 1.0
    else:
        # agreement ranges [1/n .. 1]; map to [0.5 .. 1.0].
        lo = 1.0 / n
        frac = (agreement - lo) / (1.0 - lo) if (1.0 - lo) > 0 else 1.0
        mult = round(0.5 + 0.5 * frac, 4)

    return DiversityMetrics(
        n_members=n,
        distinct_verdicts=distinct,
        agreement_ratio=round(agreement, 4),
        normalized_entropy=round(norm_entropy, 4),
        diversity_multiplier=mult,
        unanimous=(distinct == 1),
    )
