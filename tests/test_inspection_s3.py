"""Sprint 3 — inspection depth B4, B5, B7, B8 (review §8 group B)."""
from src.inspection.tls_inspector import TLSInspector
from src.inspection.whois_enricher import WhoisEnricher
from src.inspection.har_collector import HarCollector
from src.inspection.ad_creative_capture import AdCreativeCapture
from src.integrations.brightdata import get_cost_tracker


def test_tls_input_dependent_and_detects_self_signed():
    insp = TLSInspector()
    results = [insp.inspect(f"host{i}.evil") for i in range(20)]
    assert len({r.ja3 for r in results}) == 20  # fingerprint varies per host
    assert {r.is_self_signed for r in results} == {True, False}
    assert all(r.chain_subjects for r in results)


def test_tls_self_signed_has_no_sct():
    insp = TLSInspector()
    for i in range(50):
        r = insp.inspect(f"h{i}.x")
        if r.is_self_signed:
            assert r.sct_count == 0


def test_whois_enricher_records_cost_and_asn():
    t = get_cost_tracker(); t.reset()
    w = WhoisEnricher(tenant_id="wt").enrich("evil.top")
    assert w.asn.startswith("AS")
    assert w.as_org
    assert t.tenant_total("wt") > 0


def test_whois_flags_bulletproof_hosting():
    w = WhoisEnricher()
    flags = [w.enrich(f"d{i}.top").is_bulletproof_host for i in range(60)]
    assert True in flags  # some hosts land on a bulletproof ASN


def test_har_collector_per_resource_hash_and_waterfall():
    cap = HarCollector().collect("https://evil-acme.top/login")
    assert len(cap.entries) >= 8
    assert all(len(e.body_sha256) == 64 for e in cap.entries)
    assert cap.total_time_ms == sum(e.time_ms for e in cap.entries)
    assert cap.external_origins  # at least one external origin tagged


def test_har_input_dependent():
    a = HarCollector().collect("https://a.evil")
    b = HarCollector().collect("https://b.evil")
    assert len(a.entries) != len(b.entries) or \
        [e.url for e in a.entries] != [e.url for e in b.entries]


def test_ad_creative_capture_combines_two_bd_products():
    t = get_cost_tracker(); t.reset()
    ad = AdCreativeCapture(tenant_id="adt").capture("https://ads.google.com/x")
    assert ad.advertiser and ad.creative_id and ad.landing_url
    assert ad.ocr_text
    # uses both web_scraper (metadata) and scraping_browser (screenshot)
    assert {"web_scraper", "scraping_browser"} <= set(t.product_breakdown())


def test_ad_creative_input_dependent():
    cap = AdCreativeCapture()
    a = cap.capture("https://ads.google.com/aaa")
    b = cap.capture("https://ads.google.com/bbb")
    assert a.creative_id != b.creative_id
