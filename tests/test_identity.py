"""Tests for the v0.3 identity layer: RBAC, security primitives, auth flows."""
from __future__ import annotations

import pyotp
import pytest
from sqlalchemy import select

from src.common import identity as idsvc
from src.common import security
from src.common.rbac import (
    Feature,
    Permission,
    Role,
    Tier,
    limits_for,
    permissions_for,
    role_has,
    tier_has_feature,
)
from src.storage.db import session_scope
from src.storage.identity_models import AccountRow
from src.storage.init_db import init_db


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


# ───────────────────────── RBAC matrix ──────────────────────────────────

class TestRbacMatrix:
    def test_segregation_of_duties_analyst_cannot_approve(self):
        assert not role_has(Role.ANALYST, Permission.TAKEDOWN_APPROVE)
        assert not role_has(Role.ANALYST, Permission.REVIEW_DECIDE)

    def test_reviewer_can_approve(self):
        assert role_has(Role.REVIEWER, Permission.TAKEDOWN_APPROVE)
        assert role_has(Role.REVIEWER, Permission.REVIEW_DECIDE)

    def test_admin_cannot_touch_billing_or_delete_account(self):
        assert not role_has(Role.ADMIN, Permission.BILLING_MANAGE)
        assert not role_has(Role.ADMIN, Permission.ACCOUNT_MANAGE)

    def test_owner_has_billing(self):
        assert role_has(Role.OWNER, Permission.BILLING_MANAGE)

    def test_viewer_is_read_only(self):
        perms = permissions_for(Role.VIEWER)
        assert Permission.ALERTS_READ in perms
        assert Permission.ALERTS_TRIAGE not in perms
        assert Permission.TAKEDOWN_DRAFT not in perms

    def test_service_role_can_never_decide(self):
        perms = permissions_for(Role.SERVICE)
        assert Permission.REVIEW_DECIDE not in perms
        assert Permission.TAKEDOWN_APPROVE not in perms
        assert Permission.ALERTS_READ in perms

    def test_platform_has_everything(self):
        assert permissions_for(Role.PLATFORM) == {p for p in Permission}


class TestTiers:
    def test_personal_has_no_sso(self):
        assert not tier_has_feature(Tier.PERSONAL, Feature.SSO)

    def test_enterprise_has_all_features(self):
        for f in Feature:
            assert tier_has_feature(Tier.ENTERPRISE, f)

    def test_quota_escalates_with_tier(self):
        assert limits_for(Tier.PERSONAL).max_brands == 1
        assert limits_for(Tier.ENTERPRISE).max_brands is None  # unlimited


# ─────────────────────── Security primitives ────────────────────────────

class TestSecurity:
    def test_password_roundtrip(self):
        h = security.hash_password("correct horse battery")
        assert security.verify_password("correct horse battery", h)
        assert not security.verify_password("wrong", h)

    def test_short_password_rejected(self):
        with pytest.raises(ValueError):
            security.hash_password("short")

    def test_long_password_no_collision(self):
        # The 72-byte bcrypt footgun: two long passwords that share a 72-byte
        # prefix must NOT verify against each other.
        a = "x" * 100 + "A"
        b = "x" * 100 + "B"
        h = security.hash_password(a)
        assert security.verify_password(a, h)
        assert not security.verify_password(b, h)

    def test_totp_verify(self):
        secret = security.new_mfa_secret()
        assert security.verify_totp(secret, pyotp.TOTP(secret).now())
        assert not security.verify_totp(secret, "000000")

    def test_jwt_roundtrip_and_type_check(self):
        tok = security.issue_access_token(user_id="u", account_id="a", role="reviewer")
        claims = security.decode_token(tok, expected_type="access")
        assert claims["role"] == "reviewer"
        from jose import JWTError
        with pytest.raises(JWTError):
            security.decode_token(tok, expected_type="refresh")

    def test_session_sign_load(self):
        tok = security.sign_session({"sid": "abc"})
        assert security.load_session(tok)["sid"] == "abc"
        assert security.load_session("garbage") is None


# ───────────────────────── Identity flows ───────────────────────────────

class TestIdentityFlows:
    def test_signup_and_login(self):
        with session_scope() as s:
            au = idsvc.signup(s, email="t1@x.com", password="password123",
                              full_name="T One", tier=Tier.PRO)
            assert au.role == Role.OWNER and au.tier == Tier.PRO
        with session_scope() as s:
            au = idsvc.authenticate_password(s, email="t1@x.com", password="password123")
            assert au.email == "t1@x.com"

    def test_duplicate_email_rejected(self):
        with session_scope() as s:
            idsvc.signup(s, email="dup@x.com", password="password123")
        with session_scope() as s, pytest.raises(idsvc.AuthError):
            idsvc.create_user(s, email="dup@x.com", password="password123")

    def test_bad_password_rejected(self):
        with session_scope() as s:
            idsvc.signup(s, email="t2@x.com", password="password123")
        with session_scope() as s, pytest.raises(idsvc.AuthError):
            idsvc.authenticate_password(s, email="t2@x.com", password="nope")

    def test_lockout_after_failures(self):
        with session_scope() as s:
            idsvc.signup(s, email="lock@x.com", password="password123")
        for _ in range(5):
            with session_scope() as s:
                try:
                    idsvc.authenticate_password(s, email="lock@x.com", password="bad")
                except idsvc.AuthError:
                    pass
        with session_scope() as s, pytest.raises(idsvc.AuthError, match="locked"):
            idsvc.authenticate_password(s, email="lock@x.com", password="password123")

    def test_mfa_flow(self):
        with session_scope() as s:
            au = idsvc.signup(s, email="mfa2@x.com", password="password123")
            uid = au.user_id
            enrol = idsvc.begin_mfa_enrolment(s, user_id=uid)
            codes = idsvc.confirm_mfa(s, user_id=uid, code=pyotp.TOTP(enrol["secret"]).now())
            secret = enrol["secret"]
        assert len(codes) == 10
        with session_scope() as s:
            with pytest.raises(idsvc.MfaRequired):
                idsvc.authenticate_password(s, email="mfa2@x.com", password="password123")
            au = idsvc.complete_mfa(s, user_id=uid, code=pyotp.TOTP(secret).now())
            assert au.email == "mfa2@x.com"

    def test_recovery_code_works_once(self):
        with session_scope() as s:
            au = idsvc.signup(s, email="rec@x.com", password="password123")
            uid = au.user_id
            enrol = idsvc.begin_mfa_enrolment(s, user_id=uid)
            codes = idsvc.confirm_mfa(s, user_id=uid, code=pyotp.TOTP(enrol["secret"]).now())
        recovery = codes[0]
        with session_scope() as s:
            au = idsvc.complete_mfa(s, user_id=uid, code=recovery)
            assert au.email == "rec@x.com"
        # same recovery code must not work twice
        with session_scope() as s, pytest.raises(idsvc.AuthError):
            idsvc.complete_mfa(s, user_id=uid, code=recovery)

    def test_session_lifecycle(self):
        with session_scope() as s:
            au = idsvc.signup(s, email="sess@x.com", password="password123")
            sid = idsvc.create_web_session(s, au, ip="1.1.1.1", user_agent="t")
        with session_scope() as s:
            assert idsvc.load_web_session(s, sid).email == "sess@x.com"
            idsvc.revoke_web_session(s, sid)
        with session_scope() as s:
            assert idsvc.load_web_session(s, sid) is None

    def test_oidc_jit_provision(self):
        with session_scope() as s:
            au = idsvc.upsert_oidc_user(
                s, issuer="https://idp.example", subject="sub-123",
                email="sso@x.com", full_name="SSO User",
            )
            assert au.email == "sso@x.com"
        # second login with same subject reuses the user
        with session_scope() as s:
            au2 = idsvc.upsert_oidc_user(
                s, issuer="https://idp.example", subject="sub-123",
                email="sso@x.com",
            )
            assert au2.user_id == au.user_id
