"""Coverage-completion tests — batch 1: pure scoring + common modules.

Targets the small per-file gaps in scoring/* and common/* that are pure logic
(no live network), exercising the specific uncovered branches.
"""
from __future__ import annotations

import math

import pytest


# ── version.py (was 0%) ──────────────────────────────────────────────
def test_version_build_identity_and_stamp():
    from src.common import version as v
    bi = v.build_identity()
    assert bi.product == "SpoofVane"
    assert bi.version == "0.5.0"
    assert bi.codename == "spoofvane-convergence-v9"
    d = bi.as_dict()
    assert d["product"] == "SpoofVane"
    assert isinstance(bi.review_lineage, tuple) and bi.review_lineage
    stamp = bi.stamp()
    assert "SpoofVane v0.5.0" in stamp and "Claude" in stamp


def test_version_artifact_footer_default_and_explicit():
    from datetime import datetime, timezone
    from src.common import version as v
    f1 = v.artifact_footer()
    assert "rendered" in f1 and "SpoofVane" in f1
    fixed = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)
    f2 = v.artifact_footer(fixed)
    assert "2026-05-29 12:00:00Z" in f2


# ── phash.py line 31 (empty inputs) ──────────────────────────────────
def test_phash_empty_inputs_return_zero():
    from src.scoring.phash import phash_score
    assert phash_score(b"", b"abc") == 0.0
    assert phash_score(b"abc", b"") == 0.0


# ── dom_similarity.py line 30 (empty cosine) ─────────────────────────
def test_dom_score_empty_html_zero():
    from src.scoring.dom_similarity import dom_score
    assert dom_score(b"", b"") == 0.0


def test_dom_score_login_mismatch_penalty():
    from src.scoring.dom_similarity import dom_score
    canon = b"<html><body><form><input type='password' name='pw'></form></body></html>"
    suspect = b"<html><body><p>hello</p></body></html>"
    # canonical has login form, suspect doesn't -> penalty branch
    s = dom_score(canon, suspect)
    assert 0.0 <= s <= 1.0


# ── composite.py lines 23,26-27 (_safe_read paths) ───────────────────
def test_composite_safe_read_missing_and_none():
    from src.scoring import composite
    assert composite._safe_read(None, ".png") == b""
    # nonexistent sha -> FileNotFoundError -> b""
    assert composite._safe_read("deadbeef" * 8, ".png") == b""


# ── calibration.py line 37 (fit with <4 samples no-op) ───────────────
def test_platt_fit_too_few_samples_noop():
    from src.scoring.calibration import PlattCalibrator, calibrate
    c = PlattCalibrator()
    a0, b0 = c.a, c.b
    c.fit([(0.6, 1), (0.2, 0)])  # <4 -> early return
    assert (c.a, c.b) == (a0, b0)


def test_platt_fit_shifts_and_calibrate():
    from src.scoring.calibration import PlattCalibrator, calibrate
    c = PlattCalibrator()
    a0 = c.a
    samples = [(0.9, 1), (0.85, 1), (0.1, 0), (0.2, 0), (0.95, 1), (0.05, 0)]
    c.fit(samples)
    assert c.a != a0  # parameters moved
    cs = calibrate(0.7, {"phash": 0.5, "dom": 0.2}, calibrator=c)
    assert 0.0 <= cs.probability <= 1.0
    assert cs.calibration == "platt"
    assert set(cs.contributions) == {"phash", "dom"}


# ── url_risk.py line 24 (empty entropy) ──────────────────────────────
def test_url_risk_entropy_empty_and_full():
    from src.scoring.url_risk import shannon_entropy, UrlRiskScorer
    assert shannon_entropy("") == 0.0
    sc = UrlRiskScorer()
    # punycode + IP host + suspicious tokens + young age -> many contrib branches
    r = sc.score("http://xn--secure-login-verify.top/account", age_days=10)
    assert r.has_punycode is True
    assert "login" in r.suspicious_tokens
    assert r.tld == "top"
    assert "age" in r.contributions
    r2 = sc.score("http://192.168.0.1/", age_days=200)
    assert r2.has_ip_host is True
    assert r2.contributions["age"] == 0.0
    r3 = sc.score("example.com")  # no scheme, low-risk tld, no age
    assert r3.tld == "com"
    assert "age" not in r3.contributions


# ── kit_signatures_ext.py line 66 (all_kit_names / js match) ─────────
def test_extended_kit_js_bundle_match():
    from src.scoring.kit_signatures_ext import fingerprint_extended, all_kit_names
    # js bundle hash for Greatness
    matches = fingerprint_extended("nothing here", js_bundle_sha256=["b1f2a3c4d5e6f708"])
    assert any(m.kit == "Greatness" and m.matched_on == "js_bundle_hash" for m in matches)
    names = all_kit_names()
    assert "16Shop" in names and "Frappo" in names
    assert len(names) >= 12


def test_extended_kit_dom_and_css_and_dom_only():
    from src.scoring.kit_signatures_ext import fingerprint_extended
    # dom + css for Mamba2FA
    dom = "mamba_sess wss://x/relay class mb-2fa"
    m = fingerprint_extended(dom)
    assert any(x.kit == "Mamba2FA" for x in m)
    # dom-only (pattern present, css absent) -> 0.62
    dom2 = "astaroth ast_otp_grab present"
    m2 = fingerprint_extended(dom2)
    assert any(x.kit == "Astaroth" and x.confidence == 0.62 for x in m2)


# ── data_residency.py line 39 (unknown region) ───────────────────────
def test_data_residency_routing_and_violation():
    from src.common.data_residency import (
        DataResidencyGuard, ResidencyViolation,
    )
    g = DataResidencyGuard()
    with pytest.raises(ValueError):
        g.set_region("t1", "MARS")
    g.set_region("t1", "EU")
    assert g.region_for("t1") == "EU"
    assert g.region_for("unknown") == "US"  # default
    proof = g.route("t1", "EU", "read")
    assert proof.crossed_boundary is False
    assert proof.endpoint.startswith("eu-west-1")
    with pytest.raises(ResidencyViolation):
        g.route("t1", "US", "write")


# ── logging.py line 44 (prod JSON renderer branch) ───────────────────
def test_logging_prod_branch(monkeypatch):
    import importlib
    import src.common.logging as L
    from src.common import settings as S
    # Force reconfigure with environment != dev to hit JSONRenderer branch.
    L._configured = False

    class _S:
        log_level = "INFO"
        environment = "prod"

    monkeypatch.setattr(L, "get_settings", lambda: _S())
    log = L.get_logger("test.prod")
    log.info("hello", k="v")
    # reset so other tests get dev config fresh
    L._configured = False
