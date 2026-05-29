"""
End-to-end pipeline orchestrator.

Wires together the five pipeline stages so callers (API, seed script, cron)
can run a brand sweep with a single function call:

    discovery -> inspection -> scoring -> verdict -> alert + delivery

The pipeline is intentionally synchronous and inline. In production this is
exactly what Celery tasks would do — one stage per task, with backoff and
retries — but for the demo a single in-process pass is easier to read and
demo, and it keeps the deliverable runnable without Redis / a broker.

The pipeline only emits an Alert when:

* scoring.above_threshold is True, AND
* verdict.verdict is PHISH or SUSPICIOUS.

Benign verdicts are recorded but do not produce alerts.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..common.ids import alert_id
from ..common.logging import get_logger
from ..common.models import (
    Alert,
    AlertStatus,
    Brand,
    InspectionResult,
    ScoringResult,
    Severity,
    SuspectURL,
    Verdict,
    VerdictResult,
)
from ..delivery.webhooks import dispatch_alert
from ..discovery.run_once import run_for_brand
from ..inspection.browser import get_inspector
from ..scoring.composite import score as run_scoring
from ..storage.blob_store import read_blob
from ..storage.db import session_scope
from ..storage.repositories import (
    AlertRepo,
    BrandRepo,
    InspectionRepo,
    ScoringRepo,
    SuspectURLRepo,
    VerdictRepo,
)
from ..verdict.claude_verdict import get_verdict_engine

logger = get_logger(__name__)


@dataclass(slots=True)
class PipelineStats:
    """Summary returned to API callers after a sweep."""

    brand_id: str
    suspects_discovered: int
    suspects_inspected: int
    suspects_above_threshold: int
    alerts_created: int
    errors: int


def run_pipeline_for_brand(
    brand_id: str,
    *,
    sources: list[str] | None = None,
    max_inspect: int = 25,
) -> PipelineStats:
    """Run discovery → ... → delivery for ``brand_id`` and return stats.

    ``max_inspect`` caps how many discovered URLs are sent through the
    (expensive) inspection layer in a single run. In production this would be
    a queue, but for the demo it keeps run time bounded.
    """
    logger.info("pipeline.start", brand_id=brand_id)

    # --- 1. Load brand and canonical assets ---------------------------------
    with session_scope() as s:
        brand = BrandRepo(s).get(brand_id)
    if brand is None:
        raise ValueError(f"Brand not found: {brand_id}")

    canonical_screenshot = _load_blob(brand.canonical_screenshot_hash, ".png")
    canonical_dom = _load_blob(brand.canonical_dom_hash, ".html")
    canonical_logo = _load_logo(brand)

    # --- 2. Discovery (sources persist suspect URLs themselves) -------------
    discovery_summaries = run_for_brand(brand, source_names=sources)
    total_queued = sum(d.queued for d in discovery_summaries)
    logger.info(
        "pipeline.discovery_done",
        brand_id=brand_id,
        total_queued=total_queued,
        per_source={d.source: d.queued for d in discovery_summaries},
    )

    # Load suspect URLs for this brand
    with session_scope() as s:
        suspects = SuspectURLRepo(s).list_for_brand(brand_id, limit=max_inspect)

    # --- 3. Inspection ------------------------------------------------------
    inspector = get_inspector()
    inspected: list[tuple[SuspectURL, InspectionResult]] = []
    errors = 0
    for susp in suspects:
        try:
            insp = inspector.inspect(brand, susp)
            with session_scope() as s:
                InspectionRepo(s).create(insp)
            inspected.append((susp, insp))
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.warning("pipeline.inspection_failed", url=susp.url, error=str(exc))
    logger.info(
        "pipeline.inspection_done", brand_id=brand_id, ok=len(inspected), err=errors
    )

    # --- 4. Scoring ---------------------------------------------------------
    scored: list[tuple[SuspectURL, InspectionResult, ScoringResult]] = []
    above_threshold = 0
    for susp, insp in inspected:
        if not insp.success:
            continue
        try:
            sc = run_scoring(
                brand,
                canonical_screenshot,
                canonical_dom,
                canonical_logo,
                None,  # canonical favicon md5 — not captured for demo brand
                insp,
            )
            with session_scope() as s:
                ScoringRepo(s).create(sc)
            scored.append((susp, insp, sc))
            if sc.above_threshold:
                above_threshold += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.warning(
                "pipeline.scoring_failed", inspection_id=insp.id, error=str(exc)
            )

    # --- 5. Verdict + alert -------------------------------------------------
    engine = get_verdict_engine()
    alerts_created = 0
    for susp, insp, sc in scored:
        if not sc.above_threshold:
            continue
        try:
            verdict = engine.decide(brand, insp, sc, canonical_screenshot)
            with session_scope() as s:
                VerdictRepo(s).create(verdict)

            if verdict.verdict in (Verdict.PHISH, Verdict.SUSPICIOUS):
                alert = _build_alert(brand, susp, insp, verdict)
                with session_scope() as s:
                    AlertRepo(s).create(alert)
                dispatch_alert(alert, brand, insp, verdict)
                alerts_created += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.warning(
                "pipeline.verdict_failed", inspection_id=insp.id, error=str(exc)
            )

    stats = PipelineStats(
        brand_id=brand_id,
        suspects_discovered=total_queued,
        suspects_inspected=len(inspected),
        suspects_above_threshold=above_threshold,
        alerts_created=alerts_created,
        errors=errors,
    )
    logger.info(
        "pipeline.done",
        brand_id=stats.brand_id,
        suspects_discovered=stats.suspects_discovered,
        suspects_inspected=stats.suspects_inspected,
        suspects_above_threshold=stats.suspects_above_threshold,
        alerts_created=stats.alerts_created,
        errors=stats.errors,
    )
    return stats


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _load_blob(sha256: str | None, suffix: str) -> bytes:
    if not sha256:
        return b""
    try:
        return read_blob(sha256, suffix)
    except FileNotFoundError:
        logger.warning("pipeline.canonical_missing", sha256=sha256, suffix=suffix)
        return b""


def _load_logo(brand: Brand) -> bytes:
    if not brand.logo_path:
        return b""
    try:
        return brand.logo_path.read_bytes()
    except FileNotFoundError:
        return b""


def _build_alert(
    brand: Brand,
    suspect: SuspectURL,
    inspection: InspectionResult,
    verdict: VerdictResult,
) -> Alert:
    severity = verdict.severity
    if verdict.verdict == Verdict.PHISH and severity == Severity.LOW:
        severity = Severity.HIGH
    return Alert(
        id=alert_id(),
        brand_id=brand.id,
        inspection_id=inspection.id,
        verdict_id=verdict.id,
        severity=severity,
        status=AlertStatus.OPEN,
        suspect_url=suspect.url,
    )
