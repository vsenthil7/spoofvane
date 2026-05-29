"""
Active-learning weight tuner.

Analyst triage outcomes are captured as FeedbackEvents (true_positive when an
alert is confirmed, false_positive when dismissed), each snapshotted with the
signal context present at decision time — attack family, kit match, cloaking
flag, and the composite score.

This module turns that accumulated feedback into *recommendations*:

1. **Per-signal precision** — for each family / kit / cloaking value, what
   fraction of alerts carrying that signal were confirmed vs dismissed?
2. **Threshold tuning** — given the score distribution of true vs false
   positives, where should the composite threshold sit to separate them?
3. **Weight nudges** — signals with high precision should pull more weight;
   signals with low precision should pull less.

Crucially this produces *proposals*, not silent mutations. A human reviews
and applies them (or the platform applies them within hard safety rails).
Unsupervised weight drift is how detection systems quietly break, so the
tuner has guardrails:

* It refuses to recommend anything until ``min_samples`` feedback events
  exist (default 20) — small samples produce noise, not signal.
* Weight nudges are capped at ``max_nudge`` (default ±0.05) per cycle.
* Recommended weights are always renormalised to sum to 1.0.
* The threshold recommendation is clamped to [0.4, 0.9] so a run of
  false positives can't push it to 0 (alert on everything) or 1 (alert on
  nothing).

The output is advisory and logged; wiring it to auto-apply on a schedule is
a deliberate operator decision, not a default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.logging import get_logger
from ..common.settings import get_settings
from ..storage import models as orm

logger = get_logger(__name__)


@dataclass(slots=True)
class SignalPrecision:
    signal_kind: str  # "attack_family" | "kit_match" | "cloaking"
    value: str
    true_positives: int
    false_positives: int

    @property
    def total(self) -> int:
        return self.true_positives + self.false_positives

    @property
    def precision(self) -> float | None:
        return (self.true_positives / self.total) if self.total else None


@dataclass(slots=True)
class ThresholdRecommendation:
    current_threshold: float
    recommended_threshold: float
    rationale: str
    tp_mean_score: float | None
    fp_mean_score: float | None
    sample_size: int


@dataclass(slots=True)
class WeightRecommendation:
    signal: str
    direction: Literal["increase", "decrease", "hold"]
    rationale: str
    suggested_nudge: float  # signed, already capped


@dataclass(slots=True)
class TuningReport:
    brand_id: str | None
    sample_size: int
    sufficient_data: bool
    signal_precision: list[SignalPrecision] = field(default_factory=list)
    threshold: ThresholdRecommendation | None = None
    weight_nudges: list[WeightRecommendation] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def analyse_feedback(
    session: Session,
    brand_id: str | None = None,
    *,
    min_samples: int | None = None,
    max_nudge: float = 0.05,
) -> TuningReport:
    """Read captured feedback and produce tuning recommendations."""
    settings = get_settings()
    threshold_min_samples = (
        min_samples if min_samples is not None else settings.active_learning_min_samples
    )

    q = select(orm.FeedbackEventRow)
    if brand_id:
        q = q.where(orm.FeedbackEventRow.brand_id == brand_id)
    events = session.scalars(q).all()

    report = TuningReport(
        brand_id=brand_id,
        sample_size=len(events),
        sufficient_data=len(events) >= threshold_min_samples,
    )

    if not report.sufficient_data:
        report.notes.append(
            f"Only {len(events)} feedback events — need ≥{threshold_min_samples} "
            f"before recommendations are statistically meaningful. Holding."
        )
        return report

    # --- 1. Per-signal precision ------------------------------------------
    report.signal_precision = _compute_signal_precision(events)

    # --- 2. Threshold recommendation --------------------------------------
    report.threshold = _recommend_threshold(events, settings.score_threshold_composite)

    # --- 3. Weight nudges -------------------------------------------------
    report.weight_nudges = _recommend_weight_nudges(report.signal_precision, max_nudge)

    logger.info(
        "active_learning.report",
        brand_id=brand_id,
        samples=len(events),
        threshold_now=report.threshold.current_threshold if report.threshold else None,
        threshold_rec=report.threshold.recommended_threshold if report.threshold else None,
        nudges=len(report.weight_nudges),
    )
    return report


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _compute_signal_precision(events: list[orm.FeedbackEventRow]) -> list[SignalPrecision]:
    """Aggregate tp/fp counts for each distinct family / kit / cloaking value."""
    buckets: dict[tuple[str, str], list[int]] = {}  # (kind,value) -> [tp,fp]

    def _bump(kind: str, value: str | None, is_tp: bool) -> None:
        if not value:
            return
        key = (kind, value)
        slot = buckets.setdefault(key, [0, 0])
        slot[0 if is_tp else 1] += 1

    for e in events:
        is_tp = e.outcome == "true_positive"
        is_fp = e.outcome == "false_positive"
        if not (is_tp or is_fp):
            continue
        _bump("attack_family", e.attack_family, is_tp)
        _bump("kit_match", e.kit_match, is_tp)
        if e.cloaking_detected:
            _bump("cloaking", "detected", is_tp)

    out = [
        SignalPrecision(
            signal_kind=kind,
            value=value,
            true_positives=tp,
            false_positives=fp,
        )
        for (kind, value), (tp, fp) in sorted(buckets.items())
    ]
    return out


def _recommend_threshold(
    events: list[orm.FeedbackEventRow], current: float
) -> ThresholdRecommendation:
    """Pick a threshold that best separates confirmed from dismissed alerts.

    Simple approach: take the midpoint between the mean composite score of
    true positives and the mean of false positives, clamped to [0.4, 0.9].
    If we don't have scores on both sides, hold the current value.
    """
    tp_scores = [
        e.composite_score for e in events
        if e.outcome == "true_positive" and e.composite_score is not None
    ]
    fp_scores = [
        e.composite_score for e in events
        if e.outcome == "false_positive" and e.composite_score is not None
    ]

    tp_mean = sum(tp_scores) / len(tp_scores) if tp_scores else None
    fp_mean = sum(fp_scores) / len(fp_scores) if fp_scores else None

    if tp_mean is None or fp_mean is None:
        return ThresholdRecommendation(
            current_threshold=current,
            recommended_threshold=current,
            rationale=(
                "Insufficient scored samples on both sides — holding current "
                "threshold. Need confirmed AND dismissed alerts with scores."
            ),
            tp_mean_score=tp_mean,
            fp_mean_score=fp_mean,
            sample_size=len(tp_scores) + len(fp_scores),
        )

    # Ideal threshold sits between fp_mean and tp_mean. If fp_mean >= tp_mean
    # the signal isn't separating well — nudge conservatively upward.
    if fp_mean < tp_mean:
        midpoint = (tp_mean + fp_mean) / 2.0
        rationale = (
            f"Confirmed alerts average {tp_mean:.2f}, dismissed average "
            f"{fp_mean:.2f}. Midpoint {midpoint:.2f} best separates them."
        )
    else:
        midpoint = current + 0.03
        rationale = (
            f"Dismissed alerts ({fp_mean:.2f}) score as high as confirmed "
            f"({tp_mean:.2f}) — composite isn't separating cleanly. Nudging "
            f"threshold up slightly and recommend reviewing scorer weights."
        )

    recommended = max(0.4, min(0.9, round(midpoint, 3)))
    return ThresholdRecommendation(
        current_threshold=current,
        recommended_threshold=recommended,
        rationale=rationale,
        tp_mean_score=round(tp_mean, 3),
        fp_mean_score=round(fp_mean, 3),
        sample_size=len(tp_scores) + len(fp_scores),
    )


def _recommend_weight_nudges(
    signal_precision: list[SignalPrecision], max_nudge: float
) -> list[WeightRecommendation]:
    """Translate per-signal precision into capped weight nudges.

    High-precision signals (≥0.85 with ≥5 samples) → increase.
    Low-precision signals (≤0.5 with ≥5 samples) → decrease.
    Everything else → hold.
    """
    recs: list[WeightRecommendation] = []
    for sp in signal_precision:
        if sp.total < 5 or sp.precision is None:
            recs.append(WeightRecommendation(
                signal=f"{sp.signal_kind}:{sp.value}",
                direction="hold",
                rationale=f"Only {sp.total} samples — too few to nudge.",
                suggested_nudge=0.0,
            ))
            continue
        if sp.precision >= 0.85:
            recs.append(WeightRecommendation(
                signal=f"{sp.signal_kind}:{sp.value}",
                direction="increase",
                rationale=(
                    f"Precision {sp.precision:.0%} over {sp.total} samples — "
                    f"reliable signal, increase its influence."
                ),
                suggested_nudge=round(max_nudge, 4),
            ))
        elif sp.precision <= 0.5:
            recs.append(WeightRecommendation(
                signal=f"{sp.signal_kind}:{sp.value}",
                direction="decrease",
                rationale=(
                    f"Precision only {sp.precision:.0%} over {sp.total} samples — "
                    f"noisy signal, reduce its influence."
                ),
                suggested_nudge=round(-max_nudge, 4),
            ))
        else:
            recs.append(WeightRecommendation(
                signal=f"{sp.signal_kind}:{sp.value}",
                direction="hold",
                rationale=f"Precision {sp.precision:.0%} is middling — hold.",
                suggested_nudge=0.0,
            ))
    return recs
