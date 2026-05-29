"""API integration + negative tests (HTTP layer, via FastAPI TestClient).

Complements the unit tests in ``test_identity.py`` by exercising the real
routes over HTTP — request parsing, status codes, cookies, headers, and the
RBAC/feature dependencies as they actually fire in a request.

Heavy emphasis on NEGATIVE paths: bad input, auth bypass attempts, privilege
escalation, tampered tokens, expired sessions, injection-shaped strings.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.common import security
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
    """Seed the demo matrix once for the HTTP tests."""
    import scripts.seed_users as su
    su.seed()
    return True


def _login(client, email, password=DEMO_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _fresh(client):
    """A TestClient sharing the app but with an empty cookie jar.

    The module-scoped client accumulates session cookies across login tests;
    negative tests that assert 'unauthenticated' must start clean.
    """
    return TestClient(client.app)


# ───────────────────────── Happy-path HTTP ──────────────────────────────

class TestAuthApiHappy:
    def test_login_returns_token_and_cookie(self, client, seeded):
        r = _login(client, "owner@business.demo")
        assert r.status_code == 200
        body = r.json()
        assert body["access_token"]
        assert body["user"]["role"] == "owner"
        assert "dd_session" in r.cookies

    def test_me_via_bearer(self, client, seeded):
        tok = _login(client, "analyst@business.demo").json()["access_token"]
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        assert r.json()["role"] == "analyst"

    def test_me_via_cookie(self, client, seeded):
        c = TestClient(client.app)
        c.post("/auth/login", json={"email": "viewer@business.demo", "password": DEMO_PASSWORD})
        r = c.get("/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "viewer"

    def test_logout_clears_session(self, client, seeded):
        c = TestClient(client.app)
        c.post("/auth/login", json={"email": "owner@pro.demo", "password": DEMO_PASSWORD})
        assert c.get("/auth/me").status_code == 200
        c.post("/auth/logout")
        # cookie cleared -> now unauthenticated
        r = c.get("/auth/me")
        assert r.status_code == 401

    def test_login_page_renders(self, client, seeded):
        r = client.get("/login")
        assert r.status_code == 200
        assert "Sign in" in r.text
        assert "owner@business.demo" in r.text  # demo table present


# ─────────────────────────── Negative paths ─────────────────────────────

class TestAuthApiNegative:
    def test_login_wrong_password(self, client, seeded):
        r = _login(client, "owner@business.demo", "wrongpassword")
        assert r.status_code == 401

    def test_login_unknown_user(self, client, seeded):
        r = _login(client, "ghost@nowhere.demo")
        assert r.status_code == 401

    def test_login_malformed_email(self, client, seeded):
        r = client.post("/auth/login", json={"email": "not-an-email", "password": "x"})
        assert r.status_code == 422  # pydantic EmailStr rejects

    def test_login_missing_fields(self, client, seeded):
        r = client.post("/auth/login", json={"email": "owner@business.demo"})
        assert r.status_code == 422

    def test_me_no_auth(self, client, seeded):
        assert _fresh(client).get("/auth/me").status_code == 401

    def test_me_garbage_bearer(self, client, seeded):
        r = _fresh(client).get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert r.status_code == 401

    def test_me_tampered_jwt(self, client, seeded):
        tok = _login(client, "owner@business.demo").json()["access_token"]
        tampered = tok[:-3] + ("aaa" if not tok.endswith("aaa") else "bbb")
        r = _fresh(client).get("/auth/me", headers={"Authorization": f"Bearer {tampered}"})
        assert r.status_code == 401

    def test_refresh_token_cannot_authenticate(self, client, seeded):
        # Using a refresh token where an access token is expected must fail.
        body = _login(client, "owner@business.demo").json()
        refresh = body["refresh_token"]
        r = _fresh(client).get("/auth/me", headers={"Authorization": f"Bearer {refresh}"})
        assert r.status_code == 401

    def test_forged_jwt_wrong_secret(self, client, seeded):
        from jose import jwt
        forged = jwt.encode(
            {"sub": "x", "account_id": "y", "role": "owner", "type": "access",
             "exp": 9999999999},
            "attacker-guessed-secret", algorithm="HS256",
        )
        r = _fresh(client).get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert r.status_code == 401

    def test_tampered_session_cookie(self, client, seeded):
        c = TestClient(client.app)
        c.post("/auth/login", json={"email": "owner@business.demo", "password": DEMO_PASSWORD})
        # Overwrite the signed cookie with garbage
        c.cookies.set("dd_session", "tampered.value.123")
        assert c.get("/auth/me").status_code == 401

    def test_signup_duplicate_conflict(self, client, seeded):
        payload = {"email": "newperson@x.com", "password": "password123"}
        assert client.post("/auth/signup", json=payload).status_code == 201
        assert client.post("/auth/signup", json=payload).status_code == 409

    def test_signup_short_password_422(self, client, seeded):
        r = client.post("/auth/signup", json={"email": "shortpw@x.com", "password": "abc"})
        assert r.status_code == 422

    @pytest.mark.parametrize("payload", [
        {"email": "x'; DROP TABLE users;--@x.com", "password": "password123"},
        {"email": "a@b.com", "password": "' OR '1'='1"},
        {"email": "<script>alert(1)</script>@x.com", "password": "password123"},
    ])
    def test_injection_shaped_input_is_safe(self, client, seeded, payload):
        # Must not 500 (no SQL execution, no template injection); 401/409/422 ok.
        r = client.post("/auth/login", json=payload)
        assert r.status_code in (401, 409, 422), r.status_code
        # And the users table must still exist afterwards.
        assert _login(client, "owner@business.demo").status_code == 200


# ───────────────────────── RBAC over HTTP ───────────────────────────────
# Mount a couple of guarded probe routes and assert the dependency fires.

class TestRbacHttp:
    @pytest.fixture(scope="class", autouse=True)
    def _probe_routes(self, client):
        from src.api.deps import require, require_feature
        from src.common.rbac import Permission, Feature
        app = client.app
        if not any(r.path == "/_probe/approve" for r in app.routes):
            @app.get("/_probe/approve", dependencies=[__import__("fastapi").Depends(require(Permission.TAKEDOWN_APPROVE))])
            def _approve():
                return {"ok": True}

            @app.get("/_probe/sso", dependencies=[__import__("fastapi").Depends(require_feature(Feature.SSO))])
            def _sso():
                return {"ok": True}
        return True

    def _bearer(self, client, email):
        return {"Authorization": f"Bearer {_login(_fresh(client), email).json()['access_token']}"}

    def test_analyst_denied_approve(self, client, seeded):
        r = client.get("/_probe/approve", headers=self._bearer(client, "analyst@business.demo"))
        assert r.status_code == 403

    def test_reviewer_allowed_approve(self, client, seeded):
        r = client.get("/_probe/approve", headers=self._bearer(client, "reviewer@business.demo"))
        assert r.status_code == 200

    def test_viewer_denied_approve(self, client, seeded):
        r = client.get("/_probe/approve", headers=self._bearer(client, "viewer@business.demo"))
        assert r.status_code == 403

    def test_unauthenticated_denied_approve(self, client, seeded):
        assert _fresh(client).get("/_probe/approve").status_code == 401

    def test_business_tier_denied_sso_feature(self, client, seeded):
        # SSO is Enterprise-only -> business owner gets 402 Payment Required.
        r = client.get("/_probe/sso", headers=self._bearer(client, "owner@business.demo"))
        assert r.status_code == 402

    def test_enterprise_tier_allowed_sso_feature(self, client, seeded):
        r = client.get("/_probe/sso", headers=self._bearer(client, "owner@enterprise.demo"))
        assert r.status_code == 200
