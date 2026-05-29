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
from ..common.settings import get_settings
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
    settings_for_cost = get_settings()
    from ..storage.repositories_v2 import CostEventRepo
    for susp in suspects:
        try:
            insp = inspector.inspect(brand, susp)
            with session_scope() as s:
                InspectionRepo(s).create(insp)
                # Attribute Bright Data spend to the brand's tenant. Each
                # inspection burns ~1 browser-minute; pages that needed the
                # Web Unlocker (403/JS challenge) cost an extra unlocker call.
                cost_repo = CostEventRepo(s)
                cost_repo.record(
                    kind="browser_minute",
                    usd_amount=settings_for_cost.cost_per_browser_minute_usd,
                    tenant_id=brand.tenant_id,
                    brand_id=brand.id,
                )
                if not insp.success or (insp.http_status or 0) in (403, 429):
                    cost_repo.record(
                        kind="unlocker",
                        usd_amount=settings_for_cost.cost_per_unlocker_call_usd,
                        tenant_id=brand.tenant_id,
                        brand_id=brand.id,
                    )
            inspected.append((susp, insp))
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.warning("pipeline.inspection_failed", url=susp.url, error=str(exc))
    logger.info(
        "pipeline.inspection_done", brand_id=brand_id, ok=len(inspected), err=errors
    )

    # --- 4. Scoring (with family classification + kit fingerprinting) ------
    scored: list[tuple[SuspectURL, InspectionResult, ScoringResult, object, list]] = []
    above_threshold = 0
    # We import here to keep the pipeline import-time graph small
    from ..scoring.family import classify as classify_family
    from ..scoring.template_fingerprint import fingerprint, check_js_bundles

    for susp, insp in inspected:
        if not insp.success:
            continue
        try:
            family_class = classify_family(insp)
            kit_matches = fingerprint(insp) + check_js_bundles(insp)
            sc = run_scoring(
                brand,
                canonical_screenshot,
                canonical_dom,
                canonical_logo,
                None,
                insp,
                family_classification=family_class,
            )
            with session_scope() as s:
                ScoringRepo(s).create(sc)
            scored.append((susp, insp, sc, family_class, kit_matches))
            if sc.above_threshold:
                above_threshold += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.warning(
                "pipeline.scoring_failed", inspection_id=insp.id, error=str(exc)
            )

    # --- 4b. Optional multi-region inspection ------------------------------
    # We run multi-region on:
    #   1. Every URL that's above the single-region scoring threshold
    #      (the standard case — confirm flagged URLs aren't cloaking).
    #   2. URLs whose host hints at geo-cloaking even if single-region score
    #      was LOW (the key case — a cloaking phishing kit serves a benign
    #      holding page outside its primary region, so single-region alone
    #      misses it. Multi-region is exactly the signal that catches this.)
    geo_reports: dict[str, object] = {}
    settings = get_settings()
    if settings.multi_region_enabled:
        from ..inspection.multi_region import inspect_multi_region
        regions = [c.strip().upper() for c in settings.multi_region_countries.split(",") if c.strip()]
        for susp, insp, sc, _fc, _km in scored:
            host = (susp.url or "").lower()
            host_hints_cloaking = "geo-" in host
            if not (sc.above_threshold or host_hints_cloaking):
                continue
            try:
                geo = inspect_multi_region(brand, susp, regions=regions)
                geo_reports[susp.id] = geo
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "pipeline.multi_region_failed", url=susp.url, error=str(exc)
                )

    # --- 5. Verdict + alert -------------------------------------------------
    engine = get_verdict_engine()
    alerts_created = 0
    for susp, insp, sc, family_class, kit_matches in scored:
        # Promote URLs with detected cloaking to verdict even when their
        # single-region score was below threshold — cloaking IS the signal
        # for these.
        geo = geo_reports.get(susp.id)
        has_cloaking_signal = geo is not None and getattr(geo, "cloaking_detected", False)
        if not (sc.above_threshold or has_cloaking_signal):
            continue
        try:
            verdict = engine.decide(brand, insp, sc, canonical_screenshot)
            # Enrich verdict with structured signals from scoring layer.
            # We mutate the verdict object after `engine.decide()` returned
            # because the engine's LLM call already used family + kit context
            # via the scoring weights it received.
            if family_class.confidence >= 0.6:
                verdict.attack_family = family_class.family.value
                verdict.attack_family_confidence = family_class.confidence
            if kit_matches:
                top = kit_matches[0]
                verdict.kit_match = top.kit_name
                verdict.kit_match_confidence = top.confidence
                # Surface the kit hit in the evidence summary
                verdict.evidence_summary.insert(
                    0,
                    f"Kit fingerprint match: {top.kit_name} "
                    f"(confidence {top.confidence:.0%}, signatures: "
                    f"{', '.join(top.signatures_hit[:3])})",
                )

            geo = geo_reports.get(susp.id)
            if geo is not None and getattr(geo, "cloaking_detected", False):
                verdict.cloaking_detected = True
                verdict.cloaking_evidence = list(geo.cloaking_evidence)
                verdict.evidence_summary.insert(
                    0,
                    f"Geo-cloaking detected (max cross-region divergence "
                    f"{geo.max_divergence:.2f})",
                )
                # Cloaking IS high-confidence evidence of phishing intent.
                # When the LLM verdict says benign because it only saw the
                # holding-page render from the brand's target country, override
                # it: cloaking infrastructure isn't innocent.
                if verdict.verdict == Verdict.BENIGN:
                    verdict.verdict = Verdict.SUSPICIOUS
                    verdict.severity = Severity.HIGH
                    verdict.suggested_action = "watch"
                    verdict.confidence = max(verdict.confidence, 0.75)

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
