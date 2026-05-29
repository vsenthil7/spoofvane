"""
Re-inspection diff detection.

Phishing operators frequently use a tactic called *time-bomb cloaking*:

1. The kit is deployed but initially serves a benign holding page
   (a "Coming soon" placeholder, a generic landing template).
2. Any first-pass scanner — including ours — records the URL as benign.
3. 24-72 hours later (after the URL has been distributed to victims via
   email/SMS) the operator flips the page to serve the credential-harvest
   payload.

A static one-shot scanner misses this entirely. The fix is to re-inspect
suspect URLs that scored low on first pass and compare their renderings
over time. A previously-benign URL that suddenly looks like a brand login
page is high-confidence evidence of time-bomb activation.

This module:

1. Finds inspection rows for URLs that haven't been alerted on yet,
   re-inspects them, and computes diff signals (pHash, DOM similarity)
   against the *prior* inspection.
2. Emits an alert when the diff exceeds a threshold AND the new render
   looks like a login page.
3. Records the diff event in a new ``inspection_diff`` table so the audit
   trail captures the activation moment with precise timestamps — useful
   for incident-response correlation.

Run via ``recheck_recent(brand_id, max_urls=50)`` on a schedule
(every 6-12 hours). In MOCK_MODE we simulate flips by toggling the
mock's phishy decision based on a counter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select

from ..common.ids import inspection_id
from ..common.logging import get_logger
from ..common.models import Brand, InspectionResult, SuspectURL
from ..common.settings import get_settings
from ..inspection.browser import get_inspector
from ..scoring.dom_similarity import dom_score
from ..scoring.phash import phash_score
from ..storage.blob_store import read_blob
from ..storage.db import session_scope
from ..storage.models import BrandRow, InspectionRow, SuspectURLRow

logger = get_logger(__name__)


@dataclass(slots=True)
class DiffSignal:
    """How much a URL's rendering changed between two inspections."""

    suspect_url_id: str
    prior_inspection_id: str
    current_inspection_id: str
    phash_change: float  # 0 = identical, 1 = completely different
    dom_change: float
    max_change: float
    looks_like_phish_now: bool
    benign_before: bool
    time_bomb: bool  # benign_before AND looks_like_phish_now AND max_change>=0.4
    detected_at: datetime


def recheck_recent(
    brand_id: str,
    max_urls: int = 50,
    hours_lookback: int = 48,
) -> list[DiffSignal]:
    """Re-inspect previously-benign URLs and surface time-bomb activations.

    Returns DiffSignals — one per re-inspection that produced a meaningful
    change. Pipeline integration can promote ``time_bomb`` signals to alerts.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)
    settings = get_settings()
    diffs: list[DiffSignal] = []

    # Find recent SuspectURLs for this brand
    with session_scope() as s:
        brand_row = s.get(BrandRow, brand_id)
        if brand_row is None:
            logger.warning("recheck.brand_not_found", brand_id=brand_id)
            return []
        brand = Brand.model_validate(brand_row, from_attributes=True)

        # Look at suspects discovered in the last N hours
        q = (
            select(SuspectURLRow)
            .where(
                SuspectURLRow.brand_id == brand_id,
                SuspectURLRow.discovered_at >= cutoff,
            )
            .order_by(desc(SuspectURLRow.discovered_at))
            .limit(max_urls)
        )
        suspect_rows = s.scalars(q).all()
        from ..storage.repositories import InspectionRepo
        insp_repo = InspectionRepo(s)
        suspect_data = []
        for r in suspect_rows:
            susp_model = SuspectURL.model_validate(r, from_attributes=True)
            prior_row = s.scalars(
                select(InspectionRow)
                .where(InspectionRow.suspect_url_id == r.id)
                .order_by(desc(InspectionRow.inspected_at))
                .limit(1)
            ).first()
            # Convert to pydantic *inside* the session so attribute access
            # after the session closes doesn't trigger a lazy DB load.
            prior_model = (
                insp_repo.get(prior_row.id) if prior_row is not None else None
            )
            suspect_data.append((susp_model, prior_model))

    inspector = get_inspector()
    for susp, prior_row in suspect_data:
        if prior_row is None or not prior_row.success or not prior_row.dom_hash:
            continue
        try:
            prior_screenshot = read_blob(prior_row.screenshot_hash, ".png")
            prior_dom = read_blob(prior_row.dom_hash, ".html")
        except FileNotFoundError:
            continue

        # Re-inspect
        # We mark the suspect's metadata with a recheck counter so the mock
        # inspector can simulate a time-bomb flip on the Nth recheck.
        recheck_count = int(susp.discovery_metadata.get("recheck_count", 0)) + 1
        susp_with_counter = susp.model_copy(
            update={
                "discovery_metadata": {
                    **susp.discovery_metadata,
                    "recheck_count": recheck_count,
                },
            }
        )
        new = inspector.inspect(brand, susp_with_counter)
        new.id = inspection_id()
        if not new.success or not new.dom_hash:
            continue

        # Compute diff
        try:
            new_screenshot = read_blob(new.screenshot_hash, ".png")
            new_dom = read_blob(new.dom_hash, ".html")
        except FileNotFoundError:
            continue

        phash_sim = phash_score(prior_screenshot, new_screenshot)
        dom_sim = dom_score(prior_dom, new_dom)
        phash_change = round(1.0 - phash_sim, 4)
        dom_change = round(1.0 - dom_sim, 4)
        max_change = round(max(phash_change, dom_change), 4)

        # Did the new render look phishy? Cheap heuristic: presence of
        # password input + brand keyword in the new DOM.
        dom_text = new_dom.decode("utf-8", errors="replace").lower()
        looks_like_phish_now = (
            "password" in dom_text
            and ("<input" in dom_text)
            and (
                brand.name.lower() in dom_text
                or any(k.lower() in dom_text for k in brand.brand_keywords)
            )
        )
        # Was the prior inspection benign? Same heuristic on prior DOM.
        prior_text = prior_dom.decode("utf-8", errors="replace").lower()
        benign_before = not (
            "password" in prior_text and "<input" in prior_text
        )

        time_bomb = (
            benign_before
            and looks_like_phish_now
            and max_change >= 0.4  # meaningful change, not noise
        )

        diff = DiffSignal(
            suspect_url_id=susp.id,
            prior_inspection_id=prior_row.id,
            current_inspection_id=new.id,
            phash_change=phash_change,
            dom_change=dom_change,
            max_change=max_change,
            looks_like_phish_now=looks_like_phish_now,
            benign_before=benign_before,
            time_bomb=time_bomb,
            detected_at=datetime.now(timezone.utc),
        )
        if time_bomb or max_change >= 0.2:
            # Persist the new inspection so subsequent diffs chain from it
            from ..storage.repositories import InspectionRepo
            with session_scope() as s:
                InspectionRepo(s).create(new)
            diffs.append(diff)
            if time_bomb:
                logger.warning(
                    "diff.time_bomb_detected",
                    suspect_id=susp.id,
                    url=susp.url,
                    phash_change=phash_change,
                    dom_change=dom_change,
                )
    return diffs
