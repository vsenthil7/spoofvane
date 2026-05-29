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


def _scoring_probes():
    from src.scoring.url_risk import UrlRiskScorer
    from src.scoring.calibration import calibrate
    from src.deepfake.voiceprint import VoiceprintScorer
    from src.deepfake.deepfake_score import DeepfakeScorer
    s = UrlRiskScorer()
    vp = VoiceprintScorer(); enr = vp.enroll(b"exec")
    df = DeepfakeScorer()
    return [
        ("C2 url_risk", lambda: [s.score(u).__dict__ for u in
            ("https://acme.com/login", "https://acme-secure.top/verify",
             "http://192.168.1.1/login", "https://xn--80ak.com/x")]),
        ("C1 calibration", lambda: [calibrate(r, {"a": r}).__dict__ for r in
            (0.1, 0.4, 0.7, 0.95)]),
        ("C9 voiceprint", lambda: [vp.score(f"clip{i}".encode(), enr).__dict__ for i in range(4)]),
        ("C10 deepfake", lambda: [df.score(f"v{i}".encode(), b"a", b"face").__dict__ for i in range(4)]),
    ]


def _verdict_agent_probes():
    from src.verdict.ensemble import GptVerdict, VerdictMerger
    from src.ai_surfaces.surfaces import ExecAttackSurface, IntelNarrator
    g = GptVerdict()
    return [
        ("D2 gpt_verdict", lambda: [g.decide({"composite": c}).__dict__ for c in (0.1, 0.5, 0.8, 0.95)]),
        ("H5 exec_surface", lambda: [ExecAttackSurface().scan(n, ["x"]).__dict__ for n in
            ("Jane A", "John B", "Sara C", "Mike D")]),
        ("H7 narrator", lambda: [{"n": IntelNarrator().narrate({"verdict": v, "url": "u"})} for v in
            ("phish", "suspicious", "benign", "phish")]),
    ]


ALL_PROBES = PROBES + _scoring_probes() + _verdict_agent_probes()


@pytest.mark.parametrize("name,probe", ALL_PROBES, ids=[p[0] for p in ALL_PROBES])
def test_module_is_input_dependent(name, probe):
    outputs = probe()
    import json
    def _ser(o):
        try:
            return json.dumps(o, sort_keys=True, default=str)
        except TypeError:
            return str(o)
    sigs = {_ser(o) for o in outputs}
    assert len(sigs) >= 3, f"{name} failed differential probe: only {len(sigs)} distinct outputs"
