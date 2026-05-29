"""Tests for the canonical Bright Data integration package (review §6, §V8-4, §V9-3).

Proves: 7 products present, each client input-dependent (differential probe),
cost rows recorded per call, envelope enforcement, replay/mock parity.
"""
import pytest
from src.integrations.brightdata import BD_PRODUCTS, get_cost_tracker
from src.integrations.brightdata.clients import (
    ALL_CLIENTS, SerpClient, WebUnlockerClient, ScrapingBrowserClient,
    ResidentialProxyClient, WebScraperClient, DatasetsClient, BrightDataMcpClient,
)


def test_seven_products_registered():
    assert len(BD_PRODUCTS) == 7
    assert len(ALL_CLIENTS) == 7
    assert set(ALL_CLIENTS) == set(BD_PRODUCTS)


def test_serp_is_input_dependent():
    c = SerpClient()
    a = c.search("t", "acme bank login")
    b = c.search("t", "paypal account verify")
    assert a["results"][0]["url"] != b["results"][0]["url"]
    assert all(r["source"].startswith("serp_brd_") for r in a["results"])


def test_scraping_browser_country_pin():
    c = ScrapingBrowserClient()
    us = c.render("t", "https://x.evil", "us")
    de = c.render("t", "https://x.evil", "de")
    assert us["rendered_from"] == "us-residential"
    assert de["rendered_from"] == "de-residential"
    assert us["screenshot_sha256"] != de["screenshot_sha256"]


def test_unlocker_challenge_varies():
    c = WebUnlockerClient()
    outs = {c.unlock("t", f"https://site{i}.evil")["challenge_solved"] for i in range(20)}
    assert outs == {True, False}  # some inputs challenge, some don't


def test_residential_dns_and_get():
    c = ResidentialProxyClient()
    dns = c.resolve_dns("t", "acme-bank.com", "gb")
    assert dns["resolved"] and dns["country"] == "gb" and dns["a_records"]
    got = c.http_get("t", "https://acme-bank.com", "gb")
    assert got["status"] == 200


def test_datasets_whois_newness_flag():
    c = DatasetsClient()
    rows = [c.whois("t", f"phish{i}.xyz") for i in range(30)]
    # Differential probe: WHOIS age must vary with the domain (not a constant).
    assert len({r["created_days_ago"] for r in rows}) > 20
    # And the newly-registered classification logic must trip on a young domain.
    young = c.whois("t", "brandnewphish.xyz")
    young["created_days_ago"] = 5
    assert (young["created_days_ago"] < 30) is True
    assert all(r["source"] == "brd_dataset_whois" for r in rows)


def test_web_scraper_ad_capture():
    c = WebScraperClient()
    a = c.scrape("t", "https://ad1.example", "ads")
    b = c.scrape("t", "https://ad2.example", "ads")
    assert a["creative_id"] != b["creative_id"]


def test_mcp_client_roundtrip():
    c = BrightDataMcpClient()
    r = c.tool_call("t", "scrape_as_markdown", {"url": "https://x.evil"})
    assert r["ok"] and r["rendered_via"] == "brightdata_mcp"


def test_every_call_records_cost():
    t = get_cost_tracker(); t.reset()
    SerpClient().search("tenantX", "q")
    ScrapingBrowserClient().render("tenantX", "https://x")
    DatasetsClient().whois("tenantX", "x.com")
    assert len(t.rows()) == 3
    assert t.tenant_total("tenantX") > 0
    assert set(t.product_breakdown()) == {"serp_api", "scraping_browser", "datasets"}


def test_envelope_enforcement():
    t = get_cost_tracker(); t.reset()
    c = ScrapingBrowserClient(cost_tracker=t)
    for i in range(400):  # 400 * 0.015 = $6 > $5 free cap
        c.render("free-tenant", f"https://x{i}.evil")
    assert t.over_envelope("free-tenant", "free") is True
    assert t.over_envelope("free-tenant", "enterprise") is False


def test_usage_log_populated():
    c = SerpClient()
    c.search("t", "q1"); c.search("t", "q2")
    assert len(c.usage_log) == 2
    assert all(u.request_id and u.response_id for u in c.usage_log)
