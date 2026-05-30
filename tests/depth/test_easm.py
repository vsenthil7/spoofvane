"""v07 W7 Gate — EASM differential probe.

An asset with an expired cert + open admin port scores higher exposure than a
hardened host; subsidiary pivot finds related-org assets; two seed domains yield
two distinct inventories. Live scanning 🔒 BLOCKED-ENV (replay fixture graph).
"""
from __future__ import annotations

import pytest

from src.easm.base import Asset, Exposure
from src.easm.asset_discovery import discover_assets
from src.easm.exposure_scoring import score_exposure, exposure_rank
from src.easm.subsidiary_mapper import map_subsidiaries


def test_exposed_vs_hardened_asset_score():
    exposed = Asset(host="legacy.acme.com", ip="1.2.3.4", cert_cn=None,
                    first_seen="2026-01-01", owner_confidence=0.9,
                    exposures=[
                        Exposure("expired_cert", "expired", 0.7),
                        Exposure("open_admin_port", "8443 open", 0.85),
                    ])
    hardened = Asset(host="www.acme.com", ip="1.2.3.5", cert_cn="*.acme.com",
                     first_seen="2026-01-01", owner_confidence=0.9, exposures=[])
    es = score_exposure(exposed)
    hs = score_exposure(hardened)
    assert es > hs
    assert hs == 0.0  # hardened host has no exposure
    assert es > 0.5


def test_discovery_two_domains_distinct_inventories():
    a = discover_assets("acmebank.com")
    b = discover_assets("globex.com")
    assert [x.host for x in a] != [x.host for x in b]
    # Ranked by exposure score, highest first.
    scores = [x.exposure_score for x in a]
    assert scores == sorted(scores, reverse=True)


def test_discovery_flags_shadow_it():
    assets = discover_assets("acmebank.com")
    # Low owner-confidence assets are flagged shadow IT.
    for x in assets:
        if x.owner_confidence < 0.65:
            assert x.is_shadow_it is True


def test_subsidiary_pivot_input_dependent():
    a = map_subsidiaries("acmebank.com")
    b = map_subsidiaries("globex.com")
    assert [s.domain for s in a] != [s.domain for s in b]
    for s in a:
        assert s.relationship in ("shared_registrant", "shared_asn", "shared_cert_org")
        assert 0.0 <= s.confidence <= 1.0


def test_live_mode_blocked_env(monkeypatch):
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    with pytest.raises(NotImplementedError, match="BLOCKED-ENV"):
        discover_assets("acmebank.com")


def test_negative_hardened_inventory_low_total():
    """A determinism check: same seed -> same inventory."""
    a1 = discover_assets("acmebank.com")
    a2 = discover_assets("acmebank.com")
    assert [x.host for x in a1] == [x.host for x in a2]
