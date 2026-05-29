"""End-to-end pipeline: discovery → inspection → scoring → verdict → alert."""

from src.common.ids import brand_id as gen_brand_id, suspect_id
from src.common.models import Brand, Source, SuspectURL
from src.common.pipeline import run_pipeline_for_brand
from src.inspection.browser import get_inspector
from src.storage.db import session_scope
from src.storage.repositories import AlertRepo, BrandRepo


def _onboard() -> Brand:
    brand = Brand(
        id=gen_brand_id(),
        name="PipelineTestBank",
        login_url="https://login.pipelinetest.example/signin",
        target_country="US",
        brand_keywords=["pipelinetest"],
        score_threshold=0.65,
    )
    susp = SuspectURL(
        id=suspect_id(),
        brand_id=brand.id,
        url=str(brand.login_url),
        source=Source.MANUAL,
    )
    canonical = get_inspector().inspect(brand, susp)
    brand.canonical_screenshot_hash = canonical.screenshot_hash
    brand.canonical_dom_hash = canonical.dom_hash
    with session_scope() as s:
        return BrandRepo(s).create(brand)


def test_pipeline_runs_end_to_end_in_mock_mode() -> None:
    brand = _onboard()
    stats = run_pipeline_for_brand(brand.id, max_inspect=10)
    # Discovery is mocked → at least some URLs were queued
    assert stats.suspects_discovered > 0
    # At least one inspection should have happened
    assert stats.suspects_inspected > 0

    # Alerts exist for the brand (in mock mode some discovered URLs hit
    # phishy heuristics and produce alerts)
    with session_scope() as s:
        alerts = AlertRepo(s).list_for_brand(brand.id)
    assert stats.alerts_created == len(alerts)
