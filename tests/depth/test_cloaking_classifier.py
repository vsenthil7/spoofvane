"""v07 D6 Gate — multi-region cloaking classifier differential probe.

geo_targeted: a minority region sees distinct (attack) content vs a consistent
majority; consistent: all regions agree; block_page: some regions blocked while
others render; fragmented: many distinct renders. Distinct region-signature sets
produce distinct classifications. Pure/offline.
"""
from __future__ import annotations

from src.inspection.cloaking_classifier import RegionSignature, classify_cloaking


def test_geo_targeted_minority_is_attack():
    sigs = [
        RegionSignature("US", "attack_hash"),
        RegionSignature("GB", "clean_hash"),
        RegionSignature("DE", "clean_hash"),
        RegionSignature("BR", "clean_hash"),
        RegionSignature("IN", "clean_hash"),
    ]
    c = classify_cloaking(sigs)
    assert c.pattern == "geo_targeted"
    assert c.minority_regions == ["US"]   # the odd one out is the targeted region
    assert c.distinct_renders == 2


def test_consistent_no_cloaking():
    sigs = [RegionSignature(r, "same_hash") for r in ("US", "GB", "DE")]
    c = classify_cloaking(sigs)
    assert c.pattern == "consistent"
    assert c.distinct_renders == 1
    assert c.minority_regions == []


def test_block_page_pattern():
    sigs = [
        RegionSignature("US", "page_hash", rendered=True),
        RegionSignature("GB", "", rendered=False),
        RegionSignature("DE", "", rendered=False),
    ]
    c = classify_cloaking(sigs)
    assert c.pattern == "block_page"
    assert set(c.blocked_regions) == {"GB", "DE"}


def test_fragmented_many_distinct():
    sigs = [
        RegionSignature("US", "h1"),
        RegionSignature("GB", "h2"),
        RegionSignature("DE", "h3"),
        RegionSignature("BR", "h4"),
    ]
    c = classify_cloaking(sigs)
    assert c.pattern == "fragmented"
    assert c.distinct_renders == 4


def test_distinct_inputs_distinct_patterns():
    geo = classify_cloaking([RegionSignature("US", "a"), RegionSignature("GB", "b"),
                             RegionSignature("DE", "b"), RegionSignature("BR", "b")])
    consistent = classify_cloaking([RegionSignature("US", "x"), RegionSignature("GB", "x")])
    assert geo.pattern != consistent.pattern


def test_empty_signatures():
    c = classify_cloaking([])
    assert c.pattern == "consistent"
    assert c.n_regions == 0
