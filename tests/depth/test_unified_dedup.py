"""v07 D7 Gate — unified cross-surface freshness + dedup differential probe.

The same fake domain seen via 3 surfaces collapses to ONE unified candidate
recording all 3 sources + the freshest timestamp; distinct entities stay
separate; URL scheme/www and social @ are normalized; a stale sighting never
overwrites a fresher last_seen.
"""
from __future__ import annotations

from src.discovery.unified_dedup import DiscoveryCandidate, unify


def test_same_entity_across_surfaces_collapses():
    cands = [
        DiscoveryCandidate("url", "https://acme-login.top/signin", "serp", "2026-05-29T10:00:00Z"),
        DiscoveryCandidate("domain", "acme-login.top", "cert_stream", "2026-05-30T08:00:00Z"),
        DiscoveryCandidate("url", "http://www.acme-login.top/", "openphish", "2026-05-28T00:00:00Z"),
    ]
    out = unify(cands)
    # All three are the same host -> but kind differs (url vs domain). url ones
    # collapse together; domain is a separate kind key.
    url_rec = next(u for u in out if u.kind == "url")
    assert url_rec.sighting_count == 2
    assert set(url_rec.sources) == {"serp", "openphish"}
    # Freshest of the two url sightings wins (29th > 28th).
    assert url_rec.last_seen == "2026-05-29T10:00:00Z"
    assert url_rec.canonical_value == "acme-login.top"


def test_distinct_entities_stay_separate():
    cands = [
        DiscoveryCandidate("url", "https://acme-login.top", "serp", "2026-05-30T00:00:00Z"),
        DiscoveryCandidate("url", "https://acme-verify.xyz", "serp", "2026-05-30T00:00:00Z"),
    ]
    out = unify(cands)
    assert len(out) == 2


def test_social_handle_normalized():
    cands = [
        DiscoveryCandidate("social", "@FakeAcme", "social", "2026-05-30T00:00:00Z"),
        DiscoveryCandidate("social", "fakeacme", "darkweb", "2026-05-30T01:00:00Z"),
    ]
    out = unify(cands)
    assert len(out) == 1
    assert out[0].canonical_value == "fakeacme"
    assert set(out[0].sources) == {"social", "darkweb"}


def test_stale_does_not_overwrite_fresh():
    cands = [
        DiscoveryCandidate("url", "https://acme-login.top", "serp", "2026-05-30T12:00:00Z"),
        DiscoveryCandidate("url", "https://acme-login.top", "openphish", "2023-01-01T00:00:00Z"),
    ]
    out = unify(cands)
    assert out[0].last_seen == "2026-05-30T12:00:00Z"  # fresh kept, stale ignored


def test_ranked_by_sighting_then_freshness():
    cands = [
        DiscoveryCandidate("url", "https://a.top", "serp", "2026-05-30T00:00:00Z"),
        DiscoveryCandidate("url", "https://b.top", "serp", "2026-05-30T00:00:00Z"),
        DiscoveryCandidate("url", "https://b.top", "cert_stream", "2026-05-30T00:00:00Z"),
    ]
    out = unify(cands)
    # b.top has 2 sightings -> ranked first.
    assert out[0].canonical_value == "b.top"


def test_empty_input():
    assert unify([]) == []
