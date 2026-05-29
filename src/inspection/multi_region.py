"""
Multi-region inspection.

Modern phishing kits geo-target — the payload only renders to IPs in the
victim's country. An EU scanner sees a clean page; a US victim sees the phish.
The most reliable detection signal for this class of attack is *geo-discrepancy*:
render the same URL from N regions and compare what comes back.

If the page looks substantially different from region A vs region B, that is
high-confidence evidence of cloaking — the page is hiding something from at
least one observer.

This module orchestrates parallel inspections across regions, computes pairwise
similarity between the resulting renders, and emits a structured
``GeoDiscrepancyReport`` that the verdict layer consumes alongside the
single-region inspection.

In MOCK_MODE the multi-region behaviour is simulated: phishy hosts produce
divergent renders across regions (the canonical "geo-cloaking" pattern),
benign hosts produce consistent renders.
"""

from __future__ import annotations

import concurrent.futures as _futures
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from ..common.ids import inspection_id
from ..common.logging import get_logger
from ..common.models import Brand, InspectionResult, SuspectURL
from ..common.settings import get_settings
from ..scoring.dom_similarity import dom_score
from ..scoring.phash import phash_score
from ..storage.blob_store import read_blob
from .browser import get_inspector

logger = get_logger(__name__)


# Default rendering regions for multi-region sweeps. These are chosen to cover
# the most-targeted phishing victim geos. Customers override per-brand.
DEFAULT_REGIONS: tuple[str, ...] = ("US", "GB", "DE", "BR", "IN")


@dataclass(slots=True)
class RegionInspection:
    """The result of inspecting one URL from one country."""

    country: str
    inspection: InspectionResult


@dataclass(slots=True)
class GeoDiscrepancyReport:
    """Summary of how a URL renders across multiple regions.

    Attributes:
        suspect_url_id: the SuspectURL that was multi-region inspected
        per_region: each region's inspection result
        pairwise_phash: minimum pHash similarity across all region pairs
        pairwise_dom: minimum DOM similarity across all region pairs
        max_divergence: 1 - min(pairwise_phash, pairwise_dom)
        cloaking_detected: True iff max_divergence exceeds threshold
        cloaking_evidence: human-readable bullets for the verdict layer
        primary_region: the region whose inspection is "canonical" for
            downstream scoring (typically the brand's target_country)
    """

    suspect_url_id: str
    per_region: list[RegionInspection]
    pairwise_phash_min: float
    pairwise_dom_min: float
    max_divergence: float
    cloaking_detected: bool
    cloaking_evidence: list[str] = field(default_factory=list)
    primary_region: str = ""
    inspected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def primary_inspection(self) -> InspectionResult | None:
        for r in self.per_region:
            if r.country == self.primary_region:
                return r.inspection
        return self.per_region[0].inspection if self.per_region else None


def inspect_multi_region(
    brand: Brand,
    suspect: SuspectURL,
    regions: Sequence[str] | None = None,
    *,
    max_workers: int = 4,
) -> GeoDiscrepancyReport:
    """Render ``suspect`` from each region in ``regions`` in parallel.

    Regions default to ``DEFAULT_REGIONS`` with the brand's ``target_country``
    forced to be present.
    """
    settings = get_settings()
    targets = list(regions) if regions else list(DEFAULT_REGIONS)
    if brand.target_country not in targets:
        targets.insert(0, brand.target_country)

    inspector = get_inspector()
    per_region: list[RegionInspection] = []

    def _one(country: str) -> RegionInspection:
        # We clone the brand with a different target_country so the inspector
        # routes through a proxy pinned to that region. The result keeps the
        # original suspect_url_id so we can correlate across rows.
        region_brand = brand.model_copy(update={"target_country": country})
        result = inspector.inspect(region_brand, suspect)
        # Force a fresh inspection_id per region so each row is unique
        result.id = inspection_id()
        return RegionInspection(country=country, inspection=result)

    with _futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        for ri in pool.map(_one, targets):
            per_region.append(ri)

    # Compute pairwise minimum similarities. We're interested in the *worst*
    # match between any two regions — that's where cloaking shows up.
    pairwise_phash, pairwise_dom = _compute_pairwise_min(per_region)

    max_divergence = round(1.0 - min(pairwise_phash, pairwise_dom), 4)
    threshold = settings.geo_cloaking_threshold
    cloaking = max_divergence >= threshold

    evidence: list[str] = []
    if cloaking:
        worst_pair = _worst_region_pair(per_region)
        if worst_pair:
            a, b, ph, dm = worst_pair
            evidence.append(
                f"Renders from {a} and {b} differ substantially: "
                f"pHash={ph:.2f}, DOM={dm:.2f}"
            )
        evidence.append(
            f"Max cross-region divergence {max_divergence:.2f} ≥ threshold {threshold:.2f}"
        )
        # Detect specific cloaking patterns
        successful = [r for r in per_region if r.inspection.success]
        unsuccessful = [r for r in per_region if not r.inspection.success]
        if successful and unsuccessful:
            evidence.append(
                f"Page only rendered successfully from "
                f"{','.join(r.country for r in successful)}; "
                f"failed/blocked from {','.join(r.country for r in unsuccessful)}"
            )

    report = GeoDiscrepancyReport(
        suspect_url_id=suspect.id,
        per_region=per_region,
        pairwise_phash_min=pairwise_phash,
        pairwise_dom_min=pairwise_dom,
        max_divergence=max_divergence,
        cloaking_detected=cloaking,
        cloaking_evidence=evidence,
        primary_region=brand.target_country,
    )

    logger.info(
        "multi_region.done",
        suspect_id=suspect.id,
        regions=targets,
        phash_min=pairwise_phash,
        dom_min=pairwise_dom,
        cloaking=cloaking,
    )
    return report


# --------------------------------------------------------------------------- #
# Pairwise similarity helpers
# --------------------------------------------------------------------------- #


def _compute_pairwise_min(
    per_region: list[RegionInspection],
) -> tuple[float, float]:
    """Min pHash and min DOM similarity across all pairs of successful regions.

    Returns (1.0, 1.0) when fewer than two successful inspections exist —
    we cannot detect cloaking with only one observation.
    """
    successful = [r for r in per_region if r.inspection.success]
    if len(successful) < 2:
        return 1.0, 1.0

    min_phash = 1.0
    min_dom = 1.0
    for i in range(len(successful)):
        for j in range(i + 1, len(successful)):
            a, b = successful[i].inspection, successful[j].inspection
            ph = _safe_phash(a.screenshot_hash, b.screenshot_hash)
            dm = _safe_dom(a.dom_hash, b.dom_hash)
            min_phash = min(min_phash, ph)
            min_dom = min(min_dom, dm)
    return round(min_phash, 4), round(min_dom, 4)


def _worst_region_pair(
    per_region: list[RegionInspection],
) -> tuple[str, str, float, float] | None:
    """Return the (regionA, regionB, phash, dom) for the most divergent pair."""
    successful = [r for r in per_region if r.inspection.success]
    if len(successful) < 2:
        return None
    worst: tuple[str, str, float, float] | None = None
    worst_score = 1.0
    for i in range(len(successful)):
        for j in range(i + 1, len(successful)):
            a, b = successful[i], successful[j]
            ph = _safe_phash(a.inspection.screenshot_hash, b.inspection.screenshot_hash)
            dm = _safe_dom(a.inspection.dom_hash, b.inspection.dom_hash)
            combined = min(ph, dm)
            if combined < worst_score:
                worst_score = combined
                worst = (a.country, b.country, ph, dm)
    return worst


def _safe_phash(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 1.0
    try:
        return phash_score(read_blob(a, ".png"), read_blob(b, ".png"))
    except FileNotFoundError:
        return 1.0


def _safe_dom(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 1.0
    try:
        return dom_score(read_blob(a, ".html"), read_blob(b, ".html"))
    except FileNotFoundError:
        return 1.0
