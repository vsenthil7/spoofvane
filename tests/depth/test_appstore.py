"""v07 W2 Gate — app-store fraud differential probe.

Clone app (brand icon + excess permissions) vs benign app => distinct risk;
identical icon across stores correlates into one cluster; developer reputation
is input-dependent. Live store APIs 🔒 BLOCKED-ENV (replay default).
"""
from __future__ import annotations

import pytest

from src.discovery.appstore.base import AppStoreAdapter
from src.discovery.appstore.engine import AppStoreEngine, search_all_stores
from src.discovery.appstore.apk_analyzer import analyze_apk
from src.discovery.appstore.developer_reputation import developer_reputation

BRAND_ICON = "aabbccddeeff00112233445566778899"


def test_clone_vs_benign_distinct_risk():
    clone = analyze_apk(
        permissions=[
            "android.permission.READ_SMS", "android.permission.SYSTEM_ALERT_WINDOW",
            "android.permission.BIND_ACCESSIBILITY_SERVICE",
            "android.permission.REQUEST_INSTALL_PACKAGES",
        ],
        icon_hash=BRAND_ICON, brand_icon_hash=BRAND_ICON,
        baseline_permissions=["android.permission.INTERNET"],
    )
    benign = analyze_apk(
        permissions=["android.permission.INTERNET", "android.permission.CAMERA"],
        icon_hash="ffffffffffffffffffffffffffffffff", brand_icon_hash=BRAND_ICON,
    )
    assert clone.risk > benign.risk
    assert clone.over_broad is True
    assert benign.over_broad is False
    assert clone.icon_clone_score == 1.0 and benign.icon_clone_score < 1.0


def test_engine_two_brands_distinct_findings():
    a = search_all_stores("AcmeBank", BRAND_ICON)
    b = search_all_stores("Globex", BRAND_ICON)
    assert [(f.store, f.app_id) for f in a] != [(f.store, f.app_id) for f in b]
    sigs = [f.app_clone_signal for f in a]
    assert sigs == sorted(sigs, reverse=True)


def test_cross_store_clone_correlation():
    eng = AppStoreEngine()
    findings = eng.search("AcmeBank", BRAND_ICON)
    clusters = eng.correlate_cross_store(findings)
    # Any cloned-icon app appearing on >1 store-finding collapses into one cluster.
    for icon_hash, stores in clusters.items():
        assert len(stores) > 1  # multiple findings share this icon (cross-store clone)
    # The cloned brand icon must span at least 2 DISTINCT stores (the W2 claim).
    assert any(len(set(stores)) >= 2 for stores in clusters.values())


def test_developer_reputation_input_dependent():
    official = developer_reputation("AcmeBank Inc.", official_developer="AcmeBank Inc.")
    sketchy = developer_reputation("Dev404")
    assert official.reputation > sketchy.reputation
    assert official.verified_publisher is True


def test_live_mode_blocked_env(monkeypatch):
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    with pytest.raises(NotImplementedError, match="BLOCKED-ENV"):
        AppStoreAdapter("google_play").search("AcmeBank", BRAND_ICON)


def test_negative_no_permissions_zero_risk():
    r = analyze_apk(permissions=[], icon_hash="", brand_icon_hash=BRAND_ICON)
    assert r.risk == 0.0 and r.over_broad is False
