"""Coverage-closing functional tests: dashboard HTML, auth edges, MFA HTTP."""
from __future__ import annotations

import pyotp
import pytest
from fastapi.testclient import TestClient

from src.common.demo_users import DEMO_PASSWORD
from src.storage.init_db import init_db


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


@pytest.fixture(scope="module")
def client():
    from src.api.app import app
    return TestClient(app)


@pytest.fixture(scope="module")
def seeded():
    import scripts.seed_users as su
    su.seed()
    return True


# ─────────────────────── Dashboard HTML routes ──────────────────────────

class TestDashboardHtml:
    def test_dashboard_renders(self, client, seeded):
        r = client.get("/")
        assert r.status_code == 200
        assert "DoppelDomain" in r.text

    def test_login_page_renders(self, client, seeded):
        r = client.get("/login")
        assert r.status_code == 200 and "Sign in" in r.text

    def test_audit_page_renders(self, client, seeded):
        r = client.get("/audit")
        assert r.status_code in (200, 401, 403)

    def test_healthz(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200 and r.json()["status"] == "ok"

    def test_metrics(self, client):
        assert client.get("/metrics").status_code == 200

    def test_openapi(self, client):
        assert client.get("/openapi.json").status_code == 200


# ───────────────────────── Auth HTTP edges ──────────────────────────────

class TestAuthEdges:
    def test_signup_then_login(self, client, seeded):
        email = "freshuser@signup.example"
        r = client.post("/auth/signup", json={"email": email, "password": "password123",
                                              "full_name": "Fresh User", "tier": "pro"})
        assert r.status_code == 201
        assert r.json()["user"]["tier"] == "pro"
        # can now log in
        assert client.post("/auth/login",
                           json={"email": email, "password": "password123"}).status_code == 200

    def test_signup_enterprise_tier(self, client, seeded):
        r = client.post("/auth/signup", json={"email": "ent@signup.example",
                                              "password": "password123", "tier": "enterprise"})
        assert r.status_code == 201

    def test_mfa_enroll_and_confirm_http(self, client, seeded):
        # signup a fresh user, enroll MFA over HTTP, confirm, then login requires it
        email = "mfaenroll@mfatest.example"
        tok = client.post("/auth/signup",
                          json={"email": email, "password": "password123"}).json()["access_token"]
        H = {"Authorization": f"Bearer {tok}"}
        enroll = client.post("/auth/mfa/enroll", headers=H).json()
        assert "provisioning_uri" in enroll and "secret" in enroll
        code = pyotp.TOTP(enroll["secret"]).now()
        confirm = client.post("/auth/mfa/confirm", headers=H, json={"code": code})
        assert confirm.status_code == 200
        assert len(confirm.json()["recovery_codes"]) == 10
        # login now returns mfa_required
        r = client.post("/auth/login", json={"email": email, "password": "password123"})
        assert r.json()["mfa_required"] is True
        uid = r.json()["user_id"]
        # complete it
        v = client.post("/auth/mfa/verify",
                        json={"user_id": uid, "code": pyotp.TOTP(enroll["secret"]).now()})
        assert v.status_code == 200 and v.json()["access_token"]

    def test_mfa_confirm_bad_code_400(self, client, seeded):
        email = "mfabad@mfatest.example"
        tok = client.post("/auth/signup",
                          json={"email": email, "password": "password123"}).json()["access_token"]
        H = {"Authorization": f"Bearer {tok}"}
        client.post("/auth/mfa/enroll", headers=H)
        r = client.post("/auth/mfa/confirm", headers=H, json={"code": "000000"})
        assert r.status_code == 400

    def test_mfa_verify_wrong_code_401(self, client, seeded):
        # enable MFA on a user, then verify with wrong code
        email = "mfawrong@mfatest.example"
        tok = client.post("/auth/signup",
                          json={"email": email, "password": "password123"}).json()["access_token"]
        H = {"Authorization": f"Bearer {tok}"}
        enroll = client.post("/auth/mfa/enroll", headers=H).json()
        client.post("/auth/mfa/confirm", headers=H, json={"code": pyotp.TOTP(enroll["secret"]).now()})
        login = client.post("/auth/login", json={"email": email, "password": "password123"})
        uid = login.json()["user_id"]
        r = client.post("/auth/mfa/verify", json={"user_id": uid, "code": "111111"})
        assert r.status_code == 401

    def test_logout_without_session_ok(self, client, seeded):
        assert TestClient(client.app).post("/auth/logout").status_code == 200

    def test_oidc_login_404_when_disabled(self, client, seeded):
        # OIDC disabled by default
        assert client.get("/auth/oidc/login").status_code == 404

    def test_oidc_callback_404_when_disabled(self, client, seeded):
        r = client.get("/auth/oidc/callback?code=x&state=y")
        assert r.status_code in (404, 400)
