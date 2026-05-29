"""Differential depth probe (review §0.1 + §V8-4).

Feeds >=3 distinct inputs to each implemented Bright Data client and asserts the
outputs are input-dependent. A stub returning {"mock": True} or any constant
fails this probe. This harness is Track A's canonical gift to the other tracks
(review §10.5) — it is reusable as a pytest module.
"""
import pytest
from src.integrations.brightdata.clients import (
    SerpClient, WebUnlockerClient, ScrapingBrowserClient,
    ResidentialProxyClient, WebScraperClient, DatasetsClient, BrightDataMcpClient,
)

PROBES = [
    ("A1 serp_api", lambda: [SerpClient().search("t", q) for q in
        ("acme login", "paypal verify", "hsbc secure", "coinbase auth")]),
    ("B1 scraping_browser", lambda: [ScrapingBrowserClient().render("t", "https://x.evil", c)
        for c in ("us", "de", "gb", "sg")]),
    ("A3/A6 residential", lambda: [ResidentialProxyClient().resolve_dns("t", d)
        for d in ("a.com", "b.net", "c.org", "d.xyz")]),
    ("A6/A9 web_unlocker", lambda: [WebUnlockerClient().unlock("t", f"https://s{i}.evil")
        for i in range(4)]),
    ("A8 web_scraper", lambda: [WebScraperClient().scrape("t", f"https://ad{i}.example", "ads")
        for i in range(4)]),
    ("A4 datasets", lambda: [DatasetsClient().whois("t", d)
        for d in ("acme.com", "phish1.xyz", "fake2.top", "scam3.cc")]),
    ("F8 bd_mcp", lambda: [BrightDataMcpClient().tool_call("t", "render", {"url": f"https://u{i}"})
        for i in range(4)]),
]


@pytest.mark.parametrize("name,probe", PROBES, ids=[p[0] for p in PROBES])
def test_module_is_input_dependent(name, probe):
    outputs = probe()
    # Serialize each output to a comparable signature; require >=3 distinct.
    import json
    sigs = {json.dumps(o, sort_keys=True) for o in outputs}
    assert len(sigs) >= 3, f"{name} failed differential probe: only {len(sigs)} distinct outputs"
