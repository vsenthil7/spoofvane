"""v07 W1 Gate — social-impersonation differential probe.

Two distinct fake handles (one near-clone avatar, one unrelated) yield two
distinct clone scores; a legit/exact handle scores low; homoglyph handles are
flagged. Live platform APIs are 🔒 BLOCKED-ENV (replay default).
"""
from __future__ import annotations

import pytest

from src.discovery.social.base import (
    handle_similarity, profile_clone_score, SocialAdapter,
)
from src.discovery.social.engine import search_all_platforms


BRAND_LOGO = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def test_profile_clone_score_input_dependent():
    near = profile_clone_score(BRAND_LOGO, BRAND_LOGO)          # exact clone
    unrelated = profile_clone_score(BRAND_LOGO, "ffffffffffffffffffffffffffffffff")
    assert near == 1.0
    assert unrelated < near
    assert near != unrelated  # two distinct avatars -> two distinct scores


def test_profile_clone_score_negative_empty():
    assert profile_clone_score("", BRAND_LOGO) == 0.0
    assert profile_clone_score(BRAND_LOGO, "") == 0.0


def test_handle_similarity_homoglyph_flagged():
    # "acmebank" with o->0 / i->1 confusables is high-risk.
    risk = handle_similarity("@acmebank", "@acmebank")  # exact = self, not impersonation
    assert risk == 0.0
    homoglyph = handle_similarity("@globe", "@gl0be")
    assert homoglyph > 0.6, f"homoglyph handle should be high risk, got {homoglyph}"
    unrelated = handle_similarity("@acmebank", "@randomstuff")
    assert unrelated < homoglyph


def test_engine_two_brands_two_distinct_finding_sets():
    a = search_all_platforms("AcmeBank", "@acmebank", BRAND_LOGO)
    b = search_all_platforms("Globex", "@globex", BRAND_LOGO)
    sig_a = [(f.platform, f.handle, f.social_clone_signal) for f in a]
    sig_b = [(f.platform, f.handle, f.social_clone_signal) for f in b]
    assert sig_a != sig_b
    # Findings are ranked highest-signal first.
    sigs = [f.social_clone_signal for f in a]
    assert sigs == sorted(sigs, reverse=True)


def test_findings_carry_social_clone_signal_for_composite():
    findings = search_all_platforms("AcmeBank", "@acmebank", BRAND_LOGO)
    for f in findings:
        assert 0.0 <= f.social_clone_signal <= 1.0


def test_live_mode_blocked_env(monkeypatch):
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    with pytest.raises(NotImplementedError, match="BLOCKED-ENV"):
        SocialAdapter("x_twitter").search("AcmeBank", "@acmebank", BRAND_LOGO)
