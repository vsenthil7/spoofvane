"""Sprint 2 — new discovery sources A4, A5, A7, A10 (review §8 group A)."""
import pytest
from src.common.models import Brand, Source
from src.discovery.openphish_feed import OpenPhishFeedSource
from src.discovery.url_shortener import UrlShortenerSource
from src.discovery.registrar_feed import RegistrarFeedSource
from src.discovery.crawl_seed import CrawlSeedSource, SeedListAdapter, DarkWebMentionAdapter
from src.discovery.run_once import DEFAULT_SOURCES


@pytest.fixture
def brand():
    return Brand(id="br_1", name="Acme Bank", login_url="https://acmebank.com/login",
                 brand_keywords=["acmebank"], target_country="US")


def test_all_four_sources_registered():
    for n in ("openphish_feed", "url_shortener", "registrar_feed", "crawl_seed"):
        assert n in DEFAULT_SOURCES


def test_openphish_dedupes_and_tags(brand):
    hits = list(OpenPhishFeedSource().discover(brand))
    assert hits
    assert all(h.source == Source.OPENPHISH_FEED for h in hits)
    assert len({h.url for h in hits}) == len(hits)  # deduped
    assert all(h.discovery_metadata["ioc_schema"] == "canonical_v1" for h in hits)


def test_openphish_excludes_brand_domain(brand):
    for h in OpenPhishFeedSource().discover(brand):
        assert "acmebank.com" not in h.url


def test_url_shortener_records_full_chain(brand):
    hits = list(UrlShortenerSource().discover(brand))
    assert hits
    for h in hits:
        chain = h.discovery_metadata["redirect_chain"]
        assert len(chain) >= 2
        assert h.discovery_metadata["hop_count"] == len(chain) - 1
        assert h.url == chain[-1]  # queued the terminal URL, not the shortener


def test_url_shortener_input_dependent(brand):
    a = UrlShortenerSource(candidates=["https://bit.ly/aaa"]).expand("https://bit.ly/aaa", brand)
    b = UrlShortenerSource(candidates=["https://bit.ly/bbb"]).expand("https://bit.ly/bbb", brand)
    assert a != b


def test_registrar_feed_uses_bd_dataset_tag(brand):
    hits = list(RegistrarFeedSource().discover(brand))
    assert hits
    assert all(h.discovery_metadata["source_tag"] == "brd_dataset_whois" for h in hits)


def test_registrar_feed_records_cost():
    from src.integrations.brightdata import get_cost_tracker
    t = get_cost_tracker(); t.reset()
    b = Brand(id="b", name="X", login_url="https://x.com/login", brand_keywords=["xbrand"])
    list(RegistrarFeedSource(tenant_id="costT").discover(b))
    assert t.tenant_total("costT") > 0
    assert "datasets" in t.product_breakdown()


def test_crawl_seed_idempotent(brand):
    src = CrawlSeedSource(adapters=[SeedListAdapter(["https://evil-acme.top/login"])])
    first = list(src.discover(brand))
    second = list(src.discover(brand))
    assert len(first) == 1 and len(second) == 0


def test_crawl_seed_darkweb_adapter(brand):
    hits = list(CrawlSeedSource(adapters=[DarkWebMentionAdapter()]).discover(brand))
    assert hits
    assert all(h.discovery_metadata["adapter"] == "darkweb" for h in hits)
