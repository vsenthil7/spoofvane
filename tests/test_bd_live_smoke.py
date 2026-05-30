"""Live Bright Data SERP smoke test (opt-in).

Runs ONLY when SPOOFVANE_BD_LIVE_TEST=1 and a real key is configured — i.e. on
the developer's machine with zones created. In CI / the build sandbox it skips
(credential-free), so this never blocks the green suite. It is the cited proof
that the SERP live lane is REAL (not BLOCKED-ENV) once zones exist.

Verified working 2026-05-30 against zone `spoofvane_serp` (Full JSON):
HTTP 200, 10 organic Google results normalized to the standard shape.
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
            os.environ.setdefault(k.strip(), v.strip())


pytestmark = pytest.mark.skipif(
    os.getenv("SPOOFVANE_BD_LIVE_TEST") != "1",
    reason="live BD test opt-in only (set SPOOFVANE_BD_LIVE_TEST=1 with zones created)",
)


def test_serp_live_returns_real_results(monkeypatch):
    _load_env()
    if not os.getenv("BRIGHTDATA_API_KEY") and not os.getenv("BRIGHTDATA_API_TOKEN"):
        pytest.skip("no BD credentials configured")
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    # config reads BRIGHTDATA_API_TOKEN; alias from API_KEY if needed.
    if not os.getenv("BRIGHTDATA_API_TOKEN") and os.getenv("BRIGHTDATA_API_KEY"):
        monkeypatch.setenv("BRIGHTDATA_API_TOKEN", os.environ["BRIGHTDATA_API_KEY"])
    from src.integrations.brightdata.config import get_bd_config
    get_bd_config.cache_clear()
    from src.integrations.brightdata.clients import SerpClient
    r = SerpClient().search("live_test", "acmebank login")
    assert r["engine"] == "google"
    assert r["result_count"] >= 1
    first = r["results"][0]
    assert first["url"].startswith("http")
    assert first["title"]
    get_bd_config.cache_clear()


def test_web_unlocker_live_returns_html(monkeypatch):
    _load_env()
    if not os.getenv("BRIGHTDATA_API_KEY") and not os.getenv("BRIGHTDATA_API_TOKEN"):
        pytest.skip("no BD credentials configured")
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    if not os.getenv("BRIGHTDATA_API_TOKEN") and os.getenv("BRIGHTDATA_API_KEY"):
        monkeypatch.setenv("BRIGHTDATA_API_TOKEN", os.environ["BRIGHTDATA_API_KEY"])
    from src.integrations.brightdata.config import get_bd_config
    get_bd_config.cache_clear()
    from src.integrations.brightdata.clients import WebUnlockerClient
    r = WebUnlockerClient().unlock("live_test", "https://example.com")
    assert r["status"] == 200
    assert r["html_len"] > 0
    assert "<html" in r["html"].lower()
    get_bd_config.cache_clear()


def test_web_scraper_live_returns_page(monkeypatch):
    """Web Scraper via the live /request API (the dedicated /datasets/v3/scrape
    endpoint is not enabled on this account; /request is the supported lane)."""
    _load_env()
    if not os.getenv("BRIGHTDATA_API_KEY") and not os.getenv("BRIGHTDATA_API_TOKEN"):
        pytest.skip("no BD credentials configured")
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    if not os.getenv("BRIGHTDATA_API_TOKEN") and os.getenv("BRIGHTDATA_API_KEY"):
        monkeypatch.setenv("BRIGHTDATA_API_TOKEN", os.environ["BRIGHTDATA_API_KEY"])
    from src.integrations.brightdata.config import get_bd_config
    get_bd_config.cache_clear()
    from src.integrations.brightdata.clients import WebScraperClient
    r = WebScraperClient().scrape("live_test", "https://example.com")
    assert r["html_len"] > 0
    assert r["fields_extracted"] > 0
    assert r["source"] == "brd_request_scrape"
    get_bd_config.cache_clear()


def test_datasets_whois_live_returns_real_rdap(monkeypatch):
    """Datasets/WHOIS via the live /request API against RDAP (the dedicated
    /datasets/v3/snapshot feed is not enabled on this account)."""
    _load_env()
    if not os.getenv("BRIGHTDATA_API_KEY") and not os.getenv("BRIGHTDATA_API_TOKEN"):
        pytest.skip("no BD credentials configured")
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    if not os.getenv("BRIGHTDATA_API_TOKEN") and os.getenv("BRIGHTDATA_API_KEY"):
        monkeypatch.setenv("BRIGHTDATA_API_TOKEN", os.environ["BRIGHTDATA_API_KEY"])
    from src.integrations.brightdata.config import get_bd_config
    get_bd_config.cache_clear()
    from src.integrations.brightdata.clients import DatasetsClient
    r = DatasetsClient().whois("live_test", "google.com")
    assert r["source"] == "brd_request_rdap"
    # google.com was registered in 1997 — a real RDAP fact, not a fixture.
    assert r["registered"] and r["registered"].startswith("1997")
    get_bd_config.cache_clear()


def test_scraping_browser_cdp_gateway_reachable(monkeypatch):
    """Scraping Browser CDP gateway (brd.superproxy.io:9222) is reachable from
    this host (TCP connect). The full Playwright-over-CDP render is driven by
    src.inspection.browser; this asserts the live gateway is up."""
    _load_env()
    if not os.getenv("BRIGHTDATA_API_KEY") and not os.getenv("BRIGHTDATA_API_TOKEN"):
        pytest.skip("no BD credentials configured")
    import socket
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    from src.integrations.brightdata.config import get_bd_config
    get_bd_config.cache_clear()
    cfg = get_bd_config()
    host = cfg.cdp_endpoint.split("://", 1)[1].split(":")[0]
    s = socket.create_connection((host, 9222), timeout=15)
    s.close()
    get_bd_config.cache_clear()
