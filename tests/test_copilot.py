"""Tests for the v0.4 AI Triage Copilot (agentic tool-use loop).

These exercise the offline planner path (MOCK_MODE), which calls the same
tool handlers the live Claude agent would, so the behaviour is validated
without any network or API key.
"""

from src.common.ids import brand_id as gen_brand_id, suspect_id
from src.common.models import Brand, Source, SuspectURL
from src.common.pipeline import run_pipeline_for_brand
from src.inspection.browser import get_inspector
from src.storage.db import session_scope
from src.storage.repositories import AlertRepo, BrandRepo
from src.verdict.copilot import TriageCopilot, get_triage_copilot


def _seed_brand_with_alerts() -> Brand:
    brand = Brand(
        id=gen_brand_id(),
        name="CopilotTestBank",
        login_url="https://login.copilottest.example/signin",
        target_country="US",
        brand_keywords=["copilottest"],
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
        BrandRepo(s).create(brand)
    run_pipeline_for_brand(brand.id, max_inspect=10)
    return brand


def test_copilot_lists_alerts() -> None:
    brand = _seed_brand_with_alerts()
    result = get_triage_copilot().ask(
        "Show me the open alerts", brand_id=brand.id
    )
    assert result.model_used == "copilot-offline-planner-v1"
    # It should have queried alerts as its first step.
    assert result.steps
    assert result.steps[0].tool == "query_alerts"
    assert "alert" in result.answer.lower()


def test_copilot_explains_evidence_for_top_alert() -> None:
    brand = _seed_brand_with_alerts()
    with session_scope() as s:
        alerts = AlertRepo(s).list_for_brand(brand.id)
    if not alerts:
        # No alerts produced by the mock heuristics for this brand; the
        # copilot should still answer gracefully.
        result = get_triage_copilot().ask("Explain the evidence", brand_id=brand.id)
        assert "no matching alerts" in result.answer.lower()
        return

    result = get_triage_copilot().ask(
        "Explain the evidence for the worst alert", brand_id=brand.id
    )
    tools_used = {st.tool for st in result.steps}
    assert "query_alerts" in tools_used
    assert "get_evidence" in tools_used


def test_copilot_drafts_takedown_without_sending() -> None:
    brand = _seed_brand_with_alerts()
    with session_scope() as s:
        alerts = AlertRepo(s).list_for_brand(brand.id)
    if not alerts:
        return
    result = get_triage_copilot().ask(
        "Draft the takedown for the highest severity alert", brand_id=brand.id
    )
    tools_used = {st.tool for st in result.steps}
    assert "draft_takedown" in tools_used
    # The product's hard rule: nothing is auto-sent.
    assert "not sent" in result.answer.lower() or "human owns approval" in result.answer.lower()


def test_copilot_read_only_by_default_excludes_mutation_tool() -> None:
    cop = TriageCopilot(allow_actions=False)
    assert "mark_triaged" not in cop._handlers


def test_copilot_actions_mode_includes_mutation_tool() -> None:
    cop = TriageCopilot(allow_actions=True)
    assert "mark_triaged" in cop._handlers


def test_copilot_handles_no_results_gracefully() -> None:
    result = get_triage_copilot().ask(
        "Show critical alerts", brand_id="brand_that_does_not_exist"
    )
    assert "no matching alerts" in result.answer.lower()
    assert result.iterations == 1
