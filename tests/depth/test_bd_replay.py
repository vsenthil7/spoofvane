"""v06 §D Gate 4 — Bright Data replay-from-fixture depth probe.

For each of the 7 BD products, force SPOOFVANE_BD_MODE=replay, call the client,
and assert the response came FROM the recorded fixture file (carries the
"_fixture": true marker) — NOT the mock fallback. This proves `replay` actually
replays recorded data rather than silently degrading to the mock generator.

The `live` 24h-green path is 🔒 BLOCKED-ENV (no BD credentials/outbound in the
build sandbox) — never claimed passed here.
"""
from __future__ import annotations

import os

import pytest

from src.integrations.brightdata.config import get_bd_config
from src.integrations.brightdata.clients import (
    SerpClient, WebUnlockerClient, ScrapingBrowserClient,
    ResidentialProxyClient, WebScraperClient, DatasetsClient, BrightDataMcpClient,
)

# Recorded fixtures live in a DEDICATED dir (not the package fixtures path) so
# they don't shadow the input-dependent mock generator that the differential
# probe (test_differential.py) relies on. The replay probe opts in explicitly.
_FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "fixtures", "brightdata"
)


@pytest.fixture(autouse=True)
def _replay_mode(monkeypatch):
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "replay")
    monkeypatch.setenv("SPOOFVANE_BD_FIXTURES", _FIXTURES_DIR)
    get_bd_config.cache_clear()
    yield
    get_bd_config.cache_clear()


def _assert_from_fixture(resp: dict):
    assert resp.get("_fixture") is True, (
        "response did not come from the recorded fixture (mock fallback hit). "
        "replay must replay recorded data."
    )


def test_serp_replays_fixture():
    r = SerpClient().search("t1", "acmebank login")
    _assert_from_fixture(r)
    assert r["result_count"] == 4


def test_unlocker_replays_fixture():
    r = WebUnlockerClient().unlock("t1", "https://acmebank-secure-login.top/verify")
    _assert_from_fixture(r)
    assert r["challenge_solved"] is True


def test_scraping_browser_replays_fixture():
    r = ScrapingBrowserClient().render("t1", "https://acmebank-secure-login.top/verify", "us")
    _assert_from_fixture(r)
    assert r["rendered_from"] == "us-residential"


def test_residential_http_get_replays_fixture():
    r = ResidentialProxyClient().http_get("t1", "https://x.example", "us")
    _assert_from_fixture(r)


def test_residential_resolve_dns_replays_fixture():
    r = ResidentialProxyClient().resolve_dns("t1", "acmebank-secure-login.top", "us")
    _assert_from_fixture(r)
    assert r["resolved"] is True


def test_web_scraper_replays_fixture():
    r = WebScraperClient().scrape("t1", "https://ads.example/acmebank-promo", "ad_creatives")
    _assert_from_fixture(r)


def test_datasets_whois_replays_fixture():
    r = DatasetsClient().whois("t1", "acmebank-secure-login.top")
    _assert_from_fixture(r)
    assert r["is_newly_registered"] is True


def test_mcp_replays_fixture():
    r = BrightDataMcpClient().tool_call("t1", "scrape_as_markdown", {"url": "x"})
    _assert_from_fixture(r)


def test_all_seven_products_have_a_replay_fixture():
    """Coverage guard: each of the 7 products replays at least one fixture."""
    checks = [
        SerpClient().search("t", "q"),
        WebUnlockerClient().unlock("t", "https://a.example"),
        ScrapingBrowserClient().render("t", "https://a.example", "us"),
        ResidentialProxyClient().http_get("t", "https://a.example", "us"),
        WebScraperClient().scrape("t", "https://a.example"),
        DatasetsClient().whois("t", "a.example"),
        BrightDataMcpClient().tool_call("t", "tool", {}),
    ]
    assert all(c.get("_fixture") is True for c in checks)
