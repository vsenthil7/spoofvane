"""v07 W3 Gate — marketplace counterfeit differential probe.

Counterfeit listing vs authorized reseller => distinct verdicts; price-anomaly
detector flags >70%-below-MSRP; NLP classifier separates replica-language from
authorized language. Live marketplace APIs 🔒 BLOCKED-ENV (replay default).
"""
from __future__ import annotations

import pytest

from src.discovery.marketplace.base import MarketplaceAdapter
from src.discovery.marketplace.engine import search_all_marketplaces
from src.discovery.marketplace.listing_nlp import counterfeit_language_score
from src.discovery.marketplace.price_anomaly import price_anomaly_score


def test_counterfeit_vs_authorized_language():
    cf = counterfeit_language_score("Genuine OEM replica 1:1 super clone AAA quality")
    auth = counterfeit_language_score("Official store authorized reseller manufacturer warranty")
    assert cf.score > auth.score
    assert cf.score > 0.5
    assert auth.score == 0.0
    assert "replica" in cf.counterfeit_hits


def test_price_anomaly_flags_too_cheap():
    cheap = price_anomaly_score(price=8.0, msrp=100.0)    # 92% off
    fair = price_anomaly_score(price=95.0, msrp=100.0)    # 5% off
    assert cheap > fair
    assert cheap >= 0.6  # over the 70% threshold => high
    assert fair < 0.3


def test_price_anomaly_negative_guards():
    assert price_anomaly_score(price=10.0, msrp=0.0) == 0.0   # no MSRP
    assert price_anomaly_score(price=-5.0, msrp=100.0) == 0.0  # bad price


def test_listing_counterfeit_vs_authorized_distinct_verdict():
    """Core W3: a counterfeit listing and an authorized listing differ."""
    listings = search_all_marketplaces("AcmeShoes", msrp=120.0)
    cf = [l for l in listings if not l.authorized]
    auth = [l for l in listings if l.authorized]
    assert cf and auth, "replay should produce both counterfeit and authorized listings"
    assert max(l.listing_nlp_signal for l in cf) > max(l.listing_nlp_signal for l in auth)


def test_engine_two_brands_distinct():
    a = search_all_marketplaces("AcmeShoes", 120.0)
    b = search_all_marketplaces("Globex", 80.0)
    assert [(l.marketplace, l.seller) for l in a] != [(l.marketplace, l.seller) for l in b]
    sigs = [l.listing_nlp_signal for l in a]
    assert sigs == sorted(sigs, reverse=True)


def test_live_mode_blocked_env(monkeypatch):
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    with pytest.raises(NotImplementedError, match="BLOCKED-ENV"):
        MarketplaceAdapter("amazon").search("AcmeShoes")
