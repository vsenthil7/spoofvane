"""v07 W4 Gate — dark-web intelligence differential probe.

Two distinct leaked snippets (one current combo list naming the brand, one
stale recycled dump) => distinct freshness/risk; dedup collapses repeats; actor
profiles aggregate recurring handles. Live Tor/Telegram collection 🔒 BLOCKED-ENV;
all fixtures are SYNTHETIC.
"""
from __future__ import annotations

import pytest

from src.intel.darkweb.base import DarkWebSource, IntelHit
from src.intel.darkweb.keyword_matcher import KeywordMatcher, match_keywords
from src.intel.darkweb.actor_tracker import ActorTracker


def test_fresh_vs_stale_distinct_risk():
    res = match_keywords("AcmeBank", ["acmebank", "acmebank.com", "ceo@acmebank.com"])
    fresh = [h for h in res.hits if h.is_fresh]
    stale = [h for h in res.hits if not h.is_fresh]
    if fresh and stale:
        assert max(h.risk for h in fresh) > max(h.risk for h in stale)
    # Fresh hits are ranked above stale ones.
    freshness_order = [h.is_fresh for h in res.hits]
    assert freshness_order == sorted(freshness_order, reverse=True)


def test_two_brands_distinct_intel():
    a = match_keywords("AcmeBank", ["acmebank"])
    b = match_keywords("Globex", ["globex"])
    assert [(h.source, h.snippet) for h in a.hits] != [(h.source, h.snippet) for h in b.hits]


def test_dedup_collapses_repeats():
    # Same snippet across sources shares a dedup_key -> collapsed.
    matcher = KeywordMatcher()
    raw = matcher.collect_all("AcmeBank", ["acmebank"])
    res = matcher.match("AcmeBank", ["acmebank"])
    assert len(res.hits) <= len(raw)
    # No duplicate dedup_keys survive.
    keys = [h.dedup_key for h in res.hits]
    assert len(keys) == len(set(keys))


def test_actor_profiles_aggregate_recurring_handles():
    hits = KeywordMatcher().collect_all("AcmeBank", ["acmebank", "acmebank.com"])
    profiles = ActorTracker().build_profiles(hits)
    for p in profiles:
        assert p.hit_count >= 1
        assert p.actor.endswith("_synthetic")  # synthetic only, never real
        assert p.first_seen <= p.last_seen
    # Ranked by hit_count then risk.
    counts = [p.hit_count for p in profiles]
    assert counts == sorted(counts, reverse=True)


def test_live_mode_blocked_env(monkeypatch):
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    with pytest.raises(NotImplementedError, match="BLOCKED-ENV"):
        DarkWebSource("tor_forums").collect("AcmeBank", ["acmebank"])


def test_fixtures_are_synthetic_only():
    """Safety: no hit may contain a real-looking credential or non-synthetic actor."""
    hits = KeywordMatcher().collect_all("AcmeBank", ["acmebank"])
    for h in hits:
        assert "[synthetic]" in h.snippet
        if h.actor:
            assert h.actor.endswith("_synthetic")
