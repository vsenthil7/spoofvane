"""Live end-to-end test for POST /api/scan (DEMO-1) — opt-in.

Runs ONLY when SPOOFVANE_BD_LIVE_TEST=1 with real BD + Anthropic credentials.
Makes one real Bright Data Web Unlocker call + one real Anthropic verdict call,
so it is billable and skipped by default (never blocks the green suite).

Proof that the live "scan this URL now" loop works end-to-end against real
services, not seed/replay data.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


def _load_env() -> None:
    p = Path(__file__).resolve().parents[1] / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            # Overwrite when the current value is missing OR empty (some test
            # bootstrap sets ANTHROPIC_API_KEY="" before the .env is read).
            if v and not os.environ.get(k):
                os.environ[k] = v


pytestmark = pytest.mark.skipif(
    os.getenv("SPOOFVANE_BD_LIVE_TEST") != "1",
    reason="live scan test opt-in only (set SPOOFVANE_BD_LIVE_TEST=1 with creds)",
)


def test_scan_live_loop_benign(monkeypatch):
    _load_env()
    if not (os.getenv("BRIGHTDATA_API_KEY") or os.getenv("BRIGHTDATA_API_TOKEN")):
        pytest.skip("no BD credentials configured")
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("no Anthropic credentials configured")
    if not os.getenv("BRIGHTDATA_API_TOKEN") and os.getenv("BRIGHTDATA_API_KEY"):
        monkeypatch.setenv("BRIGHTDATA_API_TOKEN", os.environ["BRIGHTDATA_API_KEY"])
    monkeypatch.setenv("MOCK_MODE", "false")
    # The settings singleton may have cached an empty key from test bootstrap;
    # clear it so the live key is picked up.
    from src.common import settings as settings_mod
    settings_mod.get_settings.cache_clear()

    from fastapi.testclient import TestClient
    from src.api.app import app
    c = TestClient(app)
    r = c.post("/api/scan", json={"url": "https://example.com", "brand": "AcmeBank"})
    assert r.status_code == 200
    body = r.json()
    # The whole point: a real live loop, not a mock fallback.
    assert body["mode"] == "live", body
    # Real BD fetch.
    assert body["fetch"]["product"] == "Bright Data Web Unlocker"
    assert body["fetch"]["status"] == 200
    assert body["fetch"]["html_len"] > 0
    # Real LLM verdict.
    assert body["verdict"] in {"phish", "suspicious", "benign"}
    assert body["model"]  # real model id echoed back
    assert body["tokens_in"] > 0 and body["tokens_out"] > 0
    assert len(body["evidence"]) >= 1
    # example.com is the IANA reserved domain -> should not be phish.
    assert body["verdict"] == "benign"
    # Multi-LLM ensemble: at least one real model member, each with a vote +
    # token usage; merged confidence in 0..1.
    assert isinstance(body["members"], list) and len(body["members"]) >= 1
    assert "Claude" in body["models_used"]
    for m in body["members"]:
        assert m["verdict"] in {"phish", "suspicious", "benign"}
        assert m["tokens_in"] > 0
        assert 0.0 <= m["confidence"] <= 1.0
    assert 0.0 <= body["confidence"] <= 1.0
    assert isinstance(body["dissent"], bool)
