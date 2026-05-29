"""HTTP tests for the legacy admin router and API-key auth path.

Covers tenant CRUD, API-key issue/list/revoke, cost rollup, audit-log, and
tuning endpoints — all gated by the API-key ``require_auth(SCOPE_ADMIN)``
dependency. Includes the negative paths: missing key, bad key, wrong scope.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.storage.db import session_scope
from src.storage.init_db import init_db


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


@pytest.fixture(scope="module")
def client():
    from src.api.app import app
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_key():
    """Create a tenant + admin-scoped API key directly, return 'id:secret'."""
    from src.common.ids import make_id
    from src.common.security import hash_api_secret, new_api_secret
    from src.storage import models as orm
    secret = new_api_secret()
    with session_scope() as s:
        tid = make_id("tnt")
        s.add(orm.TenantRow(id=tid, name="AdminKeyTenant", plan="enterprise"))
        kid = make_id("key")
        s.add(orm.ApiKeyRow(id=kid, tenant_id=tid, name="admin",
                            scopes=["admin:*"], secret_hash=hash_api_secret(secret)))
        s.flush()
    return f"{kid}:{secret}", tid


def _H(key):
    return {"Authorization": f"ApiKey {key}"}


# ──────────────────────────── Happy paths ───────────────────────────────

class TestAdminRouter:
    def test_create_and_list_tenant(self, client, admin_key):
        key, _ = admin_key
        r = client.post("/api/admin/tenants", headers=_H(key),
                        json={"name": "NewTenantCo", "plan": "standard"})
        assert r.status_code in (201, 200)
        assert client.get("/api/admin/tenants", headers=_H(key)).status_code == 200

    def test_get_tenant(self, client, admin_key):
        key, tid = admin_key
        r = client.get(f"/api/admin/tenants/{tid}", headers=_H(key))
        assert r.status_code == 200

    def test_issue_and_list_keys(self, client, admin_key):
        key, tid = admin_key
        r = client.post(f"/api/admin/tenants/{tid}/keys", headers=_H(key),
                        json={"name": "siem", "scopes": ["alerts:read"]})
        assert r.status_code in (201, 200)
        assert client.get(f"/api/admin/tenants/{tid}/keys", headers=_H(key)).status_code == 200

    def test_costs_endpoint(self, client, admin_key):
        key, tid = admin_key
        assert client.get(f"/api/admin/tenants/{tid}/costs", headers=_H(key)).status_code == 200

    def test_audit_log_endpoint(self, client, admin_key):
        key, _ = admin_key
        assert client.get("/api/admin/audit-log", headers=_H(key)).status_code == 200

    def test_tuning_endpoint(self, client, admin_key):
        key, _ = admin_key
        assert client.get("/api/admin/tuning", headers=_H(key)).status_code == 200


# ──────────────────────────── Negative paths ────────────────────────────

class TestApiKeyAuthNegative:
    def test_no_key_when_required(self, client, admin_key, monkeypatch):
        # With REQUIRE_AUTH on, missing key -> 401
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        from src.common import settings as smod
        smod.get_settings.cache_clear()
        try:
            r = client.get("/api/admin/tenants")
            assert r.status_code == 401
        finally:
            monkeypatch.setenv("REQUIRE_AUTH", "false")
            smod.get_settings.cache_clear()

    def test_bad_key_401(self, client):
        r = client.get("/api/admin/tenants", headers=_H("badid:badsecret"))
        assert r.status_code == 401

    def test_malformed_auth_header(self, client, monkeypatch):
        monkeypatch.setenv("REQUIRE_AUTH", "true")
        from src.common import settings as smod
        smod.get_settings.cache_clear()
        try:
            # "Bearer x" is not the ApiKey scheme -> parsed None -> 401
            r = client.get("/api/admin/tenants", headers={"Authorization": "Bearer x"})
            assert r.status_code == 401
        finally:
            monkeypatch.setenv("REQUIRE_AUTH", "false")
            smod.get_settings.cache_clear()

    def test_wrong_scope_403(self, client, admin_key):
        # Issue a read-only key, then hit an admin-scoped endpoint -> 403
        key, tid = admin_key
        from src.common.ids import make_id
        from src.common.security import hash_api_secret, new_api_secret
        from src.storage import models as orm
        secret = new_api_secret()
        with session_scope() as s:
            kid = make_id("key")
            s.add(orm.ApiKeyRow(id=kid, tenant_id=tid, name="ro",
                                scopes=["alerts:read"], secret_hash=hash_api_secret(secret)))
            s.flush()
        r = client.get("/api/admin/tenants", headers=_H(f"{kid}:{secret}"))
        assert r.status_code == 403

    def test_revoke_key(self, client, admin_key):
        key, tid = admin_key
        # issue then revoke
        issued = client.post(f"/api/admin/tenants/{tid}/keys", headers=_H(key),
                             json={"name": "temp", "scopes": ["alerts:read"]})
        body = issued.json()
        kid = body.get("id") or body.get("key_id")
        if kid:
            r = client.delete(f"/api/admin/keys/{kid}", headers=_H(key))
            assert r.status_code in (200, 204)
