"""v07 D6 — multi-region cloaking classifier (scales to N regions).

multi_region.py already orchestrates parallel regional renders + pairwise
divergence. D6 adds a PURE classifier over an arbitrary set of N regional
content signatures that names the cloaking PATTERN, so the verdict layer can
explain *how* a kit cloaks, not just that divergence exists:

* geo_targeted  — a minority of regions see distinct (attack) content while the
                  majority see one consistent (decoy) page.
* block_page    — some regions are blocked/failed while others render.
* consistent    — all regions agree (benign / no cloaking).
* fragmented    — many distinct renders (load-balanced or noisy).

Pure function over signatures => fully offline-testable; no live fetch.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class RegionSignature:
    region: str
    content_hash: str       # stable hash of the rendered content
    rendered: bool = True   # False => blocked / failed to render


@dataclass
class CloakingClassification:
    pattern: str            # geo_targeted | block_page | consistent | fragmented
    n_regions: int
    distinct_renders: int
    blocked_regions: list[str]
    minority_regions: list[str]   # regions seeing the minority (likely attack) content
    confidence: float


def classify_cloaking(signatures: list[RegionSignature]) -> CloakingClassification:
    if not signatures:
        return CloakingClassification("consistent", 0, 0, [], [], 0.0)

    n = len(signatures)
    rendered = [s for s in signatures if s.rendered]
    blocked = [s.region for s in signatures if not s.rendered]

    # Block-page pattern: some rendered, some blocked.
    if blocked and rendered:
        return CloakingClassification(
            "block_page", n, len({s.content_hash for s in rendered}),
            sorted(blocked), [], confidence=round(len(blocked) / n + 0.3, 4) if len(blocked) / n < 0.7 else 0.95)

    if not rendered:
        # Everything blocked — not cloaking per se, treat as block_page.
        return CloakingClassification("block_page", n, 0, sorted(blocked), [], 0.6)

    counts = Counter(s.content_hash for s in rendered)
    distinct = len(counts)

    if distinct == 1:
        return CloakingClassification("consistent", n, 1, [], [], 0.95)

    # Geo-targeted: one dominant (decoy) render + a small minority (attack).
    most_common_hash, most_common_n = counts.most_common(1)[0]
    minority = [s.region for s in rendered if s.content_hash != most_common_hash]
    if distinct == 2 and most_common_n >= len(rendered) * 0.6:
        return CloakingClassification(
            "geo_targeted", n, distinct, sorted(blocked), sorted(minority),
            confidence=round(most_common_n / len(rendered), 4))

    # Otherwise many distinct renders.
    return CloakingClassification(
        "fragmented", n, distinct, sorted(blocked), sorted(minority),
        confidence=round(distinct / len(rendered), 4))
