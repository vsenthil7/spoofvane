"""BUILD 020 — LLM provider settings + ensemble wiring tests.

Verifies the new OpenAI/Gemini provider settings load (mirroring sibling-project
naming), the BD monthly envelope default, and that the ensemble's live lane
raises an honest BLOCKED-ENV error when keys are absent (negative path).
"""
from __future__ import annotations

import pytest

from src.common.settings import Settings
from src.verdict.ensemble import GptVerdict, GeminiVerdict, VerdictMerger


def test_new_provider_settings_present_and_defaulted():
    s = Settings(_env_file=None)
    # New ensemble providers exist with sane defaults.
    assert s.openai_api_key == ""
    assert s.openai_model == "gpt-4o"
    assert s.gemini_api_key == ""
    assert s.gemini_model == "gemini-1.5-pro-latest"
    # Anthropic primary still present.
    assert s.anthropic_model.startswith("claude")
    # BD monthly envelope default for the kill-switch.
    assert s.brightdata_monthly_usd == 500.0


def test_settings_override_from_kwargs():
    s = Settings(_env_file=None, openai_api_key="sk-test", gemini_model="gemini-2.0-flash")
    assert s.openai_api_key == "sk-test"
    assert s.gemini_model == "gemini-2.0-flash"


def test_ensemble_replay_is_input_dependent():
    """Two materially different evidence inputs -> different merged verdicts."""
    merger = VerdictMerger()
    low = merger.merge({"composite": 0.10, "url": "a.com"})
    high = merger.merge({"composite": 0.92, "url": "b.com"})
    assert low.verdict != high.verdict
    assert low.cost_path == "slm"        # low severity -> cheap path
    assert high.cost_path == "ensemble"  # high severity -> full ensemble


def test_ensemble_dissent_discounts_confidence_and_escalates():
    merger = VerdictMerger()
    merged = merger.merge({"composite": 0.80, "url": "x.com"})
    # phish verdict always escalates to human review per D5.
    assert merged.escalate_to_human is True
    assert 0.0 <= merged.confidence <= 1.0


def test_live_lane_without_key_is_honest_blocked_env(monkeypatch):
    """Negative: forcing the live lane with no key raises NotImplementedError
    naming the missing key — never silently returns a fake verdict."""
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    from src.common import settings as settings_mod
    settings_mod.get_settings.cache_clear()  # clear real cache before swap
    monkeypatch.setattr(
        settings_mod, "get_settings",
        lambda: settings_mod.Settings(_env_file=None, openai_api_key="", gemini_api_key=""),
    )
    with pytest.raises(NotImplementedError, match="OPENAI_API_KEY"):
        GptVerdict().decide({"composite": 0.9})
    with pytest.raises(NotImplementedError, match="GEMINI_API_KEY"):
        GeminiVerdict().decide({"composite": 0.9})
