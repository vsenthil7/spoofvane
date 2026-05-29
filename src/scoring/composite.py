"""Composite scoring over all sub-scores.

The four sub-scorers are blended into a single 0..1 composite score per
brand-tuneable weights. A boolean ``above_threshold`` flag tells the
verdict layer whether to spend an LLM call on the candidate.
"""
from __future__ import annotations

from ..common.logging import get_logger
from ..common.models import Brand, InspectionResult, ScoringResult
from ..common.settings import get_settings
from ..storage.blob_store import read_blob
from .dom_similarity import dom_score
from .favicon import favicon_match
from .logo import logo_score
from .phash import phash_score

log = get_logger(__name__)


def _safe_read(sha256: str | None, suffix: str) -> bytes:
    if not sha256:
        return b""
    try:
        return read_blob(sha256, suffix=suffix)
    except FileNotFoundError:
        return b""


def score(
    brand: Brand,
    canonical_screenshot: bytes,
    canonical_dom: bytes,
    canonical_logo: bytes,
    canonical_favicon_md5: str | None,
    inspection: InspectionResult,
    family_classification=None,  # type: ignore[no-untyped-def]  -- avoid scoring-family import cycle
) -> ScoringResult:
    """Compute the composite similarity score.

    ``family_classification`` (optional ``FamilyClassification`` from
    ``scoring.family.classify``) lets the scorer use kit-family-specific
    weights — e.g. crypto kits weight DOM signatures higher because the
    seed-phrase field is the most reliable signal, while M365 kits weight
    pHash higher because visual layout is the consistent giveaway.
    """
    settings = get_settings()

    suspect_screenshot = _safe_read(inspection.screenshot_hash, ".png")
    suspect_dom = _safe_read(inspection.dom_hash, ".html")

    p = phash_score(canonical_screenshot, suspect_screenshot)
    d = dom_score(canonical_dom, suspect_dom)
    l = logo_score(canonical_logo, suspect_screenshot)
    f = favicon_match(canonical_favicon_md5, inspection.favicon_hash)

    # If a family classification with confidence ≥ 0.6 is provided, use its
    # weight profile. Otherwise fall back to the brand's tuned default weights.
    if family_classification is not None and family_classification.confidence >= 0.6:
        from .family import weights_for_family
        family_weights = weights_for_family(family_classification.family)
        base_weights = {
            "phash": family_weights["phash"],
            "dom": family_weights["dom"],
            "logo": family_weights["logo"],
            "favicon": family_weights["favicon"],
        }
    else:
        base_weights = {
            "phash": settings.score_weight_phash,
            "dom": settings.score_weight_dom,
            "logo": settings.score_weight_logo,
            "favicon": settings.score_weight_favicon,
        }

    # Renormalise weights so a missing canonical (no logo, no favicon md5)
    # doesn't perpetually drag the composite down. A brand without a
    # registered logo should be judged on the signals that ARE available.
    weights = {
        "phash": base_weights["phash"] if canonical_screenshot else 0.0,
        "dom": base_weights["dom"] if canonical_dom else 0.0,
        "logo": base_weights["logo"] if canonical_logo else 0.0,
        "favicon": base_weights["favicon"] if canonical_favicon_md5 else 0.0,
    }
    total_w = sum(weights.values())
    if total_w == 0:
        composite = 0.0
    else:
        composite = (
            weights["phash"] * p
            + weights["dom"] * d
            + weights["logo"] * l
            + weights["favicon"] * (1.0 if f else 0.0)
        ) / total_w
    composite = round(min(1.0, float(composite)), 4)
    above = bool(composite >= brand.score_threshold)

    log.info(
        "score",
        inspection_id=inspection.id,
        phash=p,
        dom=d,
        logo=l,
        favicon=f,
        composite=composite,
        above_threshold=above,
        family=(family_classification.family.value if family_classification else "unclassified"),
    )

    return ScoringResult(
        inspection_id=inspection.id,
        phash_score=p,
        dom_score=d,
        logo_score=l,
        favicon_match=f,
        composite_score=composite,
        above_threshold=above,
    )
