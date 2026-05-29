"""OIDC SSO flow tests with a mocked identity provider.

Monkeypatches httpx so no real IdP is needed, exercising oidc_login and the
full oidc_callback path: state signing/verification, token exchange, userinfo
fetch, JIT user provisioning, session creation.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.storage.init_db import init_db


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


@pytest.fixture()
def oidc_env(monkeypatch):
    monkeypatch.setenv("OIDC_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-123")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "secret-123")
    monkeypatch.setenv("OIDC_REDIRECT_URL", "http://127.0.0.1:8000/auth/oidc/callback")
    from src.common import settings as smod
    smod.get_settings.cache_clear()
    yield
    monkeypatch.setenv("OIDC_ENABLED", "false")
    smod.get_settings.cache_clear()


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p


_DISCOVERY = {
    "authorization_endpoint": "https://idp.example/authorize",
    "token_endpoint": "https://idp.example/token",
    "userinfo_endpoint": "https://idp.example/userinfo",
}


def _mock_httpx(monkeypatch, *, sub="sso-sub-1", email="ssouser@corp.example", name="SSO User"):
    import httpx

    def fake_get(url, *a, **k):
        if "openid-configuration" in url:
            return _Resp(_DISCOVERY)
        if url.endswith("/userinfo"):
            return _Resp({"sub": sub, "email": email, "name": name})
        return _Resp({})

    def fake_post(url, *a, **k):
        return _Resp({"access_token": "idp-access-token", "id_token": "x"})

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)


@pytest.fixture()
def client():
    from src.api.app import app
    return TestClient(app)


class TestOidcFlow:
    def test_login_returns_authorization_url(self, client, oidc_env, monkeypatch):
        _mock_httpx(monkeypatch)
        r = client.get("/auth/oidc/login")
        assert r.status_code == 200
        url = r.json()["authorization_url"]
        assert url.startswith("https://idp.example/authorize?")
        assert "state=" in url and "client_id=client-123" in url

    def test_callback_jit_provisions_and_logs_in(self, client, oidc_env, monkeypatch):
        _mock_httpx(monkeypatch, email="newssouser@corp.example", sub="sub-new")
        # First get a valid signed state from the login endpoint
        login = client.get("/auth/oidc/login").json()
        state = login["authorization_url"].split("state=")[1].split("&")[0]
        import urllib.parse
        state = urllib.parse.unquote(state)
        r = client.get(f"/auth/oidc/callback?code=authcode123&state={state}")
        assert r.status_code == 200
        body = r.json()
        assert body["access_token"]
        assert body["user"]["email"] == "newssouser@corp.example"

    def test_callback_rejects_bad_state(self, client, oidc_env, monkeypatch):
        _mock_httpx(monkeypatch)
        r = client.get("/auth/oidc/callback?code=x&state=forged-state")
        assert r.status_code == 400

    def test_login_404_when_disabled(self, client):
        # without oidc_env fixture, OIDC is off
        from src.common import settings as smod
        smod.get_settings.cache_clear()
        assert client.get("/auth/oidc/login").status_code == 404

    def test_callback_reuses_existing_sso_user(self, client, oidc_env, monkeypatch):
        _mock_httpx(monkeypatch, sub="sub-repeat", email="repeat@corp.example")
        login = client.get("/auth/oidc/login").json()
        import urllib.parse
        state = urllib.parse.unquote(login["authorization_url"].split("state=")[1].split("&")[0])
        r1 = client.get(f"/auth/oidc/callback?code=c1&state={state}")
        uid1 = r1.json()["user"]["user_id"]
        login2 = client.get("/auth/oidc/login").json()
        state2 = urllib.parse.unquote(login2["authorization_url"].split("state=")[1].split("&")[0])
        r2 = client.get(f"/auth/oidc/callback?code=c2&state={state2}")
        assert r2.json()["user"]["user_id"] == uid1  # same user, not duplicated
