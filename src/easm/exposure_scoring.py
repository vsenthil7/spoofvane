"""W7 exposure scoring: ranks assets by exploitability x active-threat (RF model)."""
from __future__ import annotations

from .base import Asset


def score_exposure(asset: "Asset") -> float:
    """Exposure score combines the worst exposure severity with the count and
    a confidence weight. A hardened host (no exposures) scores ~0."""
    if not asset.exposures:
        return 0.0
    max_sev = max(e.severity for e in asset.exposures)
    count_factor = min(1.0, len(asset.exposures) / 3.0)
    # Higher owner confidence => more certain this is the brand's real risk.
    score = 0.7 * max_sev + 0.3 * count_factor
    return round(min(1.0, score * (0.6 + 0.4 * asset.owner_confidence)), 4)


def exposure_rank(assets: list["Asset"]) -> list["Asset"]:
    return sorted(assets, key=lambda a: a.exposure_score, reverse=True)
