"""v07 W5 Gate — credential-leak / stealer-log differential probe.

A leaked credential matching a seed tenant user => validated=true; a random
unrelated credential => validated=false. Validation NEVER auto-locks; lockout
is a separate admin-confirmed action. NHI detector finds machine secrets.
Real stealer markets 🔒 BLOCKED-ENV; SYNTHETIC fixtures only.
"""
from __future__ import annotations

import pytest

from src.intel.credleak.base import ExposureType
from src.intel.credleak.stealer_log_parser import parse_stealer_log
from src.intel.credleak.idp_validator import IdpValidator, validate_exposure
from src.intel.credleak.nhi_detector import detect_nhi

_SYNTHETIC_LOG = """# synthetic stealer log
https://portal.acmebank.com/login:jane@acmebank.com:Pa55word!
COOKIE host=portal.acmebank.com
https://random-site.example/login:bob@nowhere.example:hunter2
"""

KNOWN = {"jane@acmebank.com", "ceo@acmebank.com"}


def test_validated_vs_unvalidated_exposure():
    exposures = parse_stealer_log(_SYNTHETIC_LOG)
    v = IdpValidator(known_identities=KNOWN)
    results = [v.validate(e) for e in exposures]
    jane = next(e for e in results if e.identity == "jane@acmebank.com")
    bob = next(e for e in results if e.identity == "bob@nowhere.example")
    assert jane.validated is True
    assert bob.validated is False
    assert jane.risk > bob.risk  # validated real account scores higher


def test_validation_does_not_lock():
    """Validation must NEVER auto-lock — separate switch (Flare pattern)."""
    e = parse_stealer_log("https://acmebank.com/login:jane@acmebank.com:x")[0]
    validate_exposure(e, KNOWN)
    assert e.validated is True
    assert e.locked is False  # critical: not locked by validation


def test_lockout_requires_admin_and_validation():
    e = parse_stealer_log("https://acmebank.com/login:jane@acmebank.com:x")[0]
    v = IdpValidator(known_identities=KNOWN)
    v.validate(e)
    # No admin confirmation -> refused.
    with pytest.raises(PermissionError):
        v.lock_account(e, admin_confirmed=False)
    # Admin confirmed -> locked.
    v.lock_account(e, admin_confirmed=True)
    assert e.locked is True


def test_cannot_lock_unvalidated():
    e = parse_stealer_log("https://x.example/login:bob@nowhere.example:x")[0]
    v = IdpValidator(known_identities=KNOWN)
    v.validate(e)
    with pytest.raises(ValueError):
        v.lock_account(e, admin_confirmed=True)


def test_session_cookie_raises_exposure_type():
    exposures = parse_stealer_log(_SYNTHETIC_LOG)
    jane = next(e for e in exposures if e.identity == "jane@acmebank.com")
    assert jane.exposure_type == ExposureType.SESSION  # had a cookie line
    assert jane.session_cookie_present is True


def test_nhi_detection_finds_machine_secrets_redacted():
    text = "leak dump AKIAIOSFODNN7EXAMPLE and ghp_" + "a" * 36 + " plus noise"
    hits = detect_nhi(text)
    kinds = {h.kind for h in hits}
    assert "aws_access_key" in kinds
    assert "github_pat" in kinds
    # Secrets are redacted in the preview, never echoed in full.
    for h in hits:
        assert "…" in h.match_preview


def test_negative_no_nhi():
    assert detect_nhi("just some ordinary text with no secrets") == []
