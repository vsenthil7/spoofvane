"""HTTP tests for the build-065 console read-surfaces that turn the Flutter
SEED screens LIVE: /api/pricing, /api/compliance, /api/admin/tenants,
/api/usage, /api/admin/demo-health.

Each shapes a real backend source (pricing catalogue, compliance modules,
TenantRepo, cost/alert data) into the flat objects the console renders. The
tests assert 200 + the documented shape so the screens run on LIVE data with
the offline seed only as a fallback.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.storage.init_db import init_db


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


@pytest.fixture(scope="module")
def client():
    from src.api.app import app
    return TestClient(app)


class TestPricing:
    def test_pricing_returns_four_tiers(self, client):
        r = client.get("/api/pricing")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        ids = {p["id"] for p in body}
        assert {"free", "pro", "business", "enterprise"} <= ids

    def test_pricing_shape_and_highlight(self, client):
        body = client.get("/api/pricing").json()
        for p in body:
            assert {"id", "name", "price_monthly", "price_monthly_monthly",
                    "tagline", "features", "highlighted", "cta"} <= set(p)
            assert isinstance(p["features"], list) and p["features"]
        # Exactly one highlighted (most-popular) plan, and it's Business.
        highlighted = [p for p in body if p["highlighted"]]
        assert len(highlighted) == 1 and highlighted[0]["id"] == "business"

    def test_enterprise_is_custom_priced(self, client):
        body = client.get("/api/pricing").json()
        ent = next(p for p in body if p["id"] == "enterprise")
        assert ent["price_monthly"] < 0  # custom / contact sales
        assert ent["cta"] == "Contact sales"

    def test_pro_annual_cheaper_than_monthly(self, client):
        body = client.get("/api/pricing").json()
        pro = next(p for p in body if p["id"] == "pro")
        assert pro["price_monthly"] < pro["price_monthly_monthly"]


class TestCompliance:
    def test_compliance_returns_controls(self, client):
        r = client.get("/api/compliance")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list) and body
        for c in body:
            assert {"framework", "control_id", "title", "status", "evidence"} <= set(c)
            assert c["status"] in {"met", "partial", "gap", "n/a"}

    def test_compliance_spans_multiple_frameworks(self, client):
        body = client.get("/api/compliance").json()
        frameworks = {c["framework"] for c in body}
        # Real NIST AI RMF controls + the standing auditor frameworks.
        assert "NIST AI RMF" in frameworks
        assert {"SOC 2", "ISO 27001", "DORA", "NIS2"} <= frameworks

    def test_compliance_includes_real_nist_evidence(self, client):
        body = client.get("/api/compliance").json()
        nist = [c for c in body if c["framework"] == "NIST AI RMF"]
        assert nist
        # Evidence strings reference real modules, not placeholders.
        assert any("eu_ai_act" in c["evidence"] or "provenance" in c["evidence"]
                   for c in nist)


class TestTenants:
    def test_tenants_shape(self, client):
        r = client.get("/api/console/tenants")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        for t in body:
            assert {"id", "name", "plan", "region", "seats", "active"} <= set(t)


class TestUsage:
    def test_usage_shape(self, client):
        r = client.get("/api/usage")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        for m in body:
            assert {"name", "used", "included", "unit"} <= set(m)


class TestDemoHealth:
    def test_demo_health_shape(self, client):
        r = client.get("/api/console/demo-health")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list) and body
        for row in body:
            assert {"check", "ok", "detail"} <= set(row)
        # The 21-page coverage check is always present and true.
        cov = next((row for row in body if "coverage" in row["check"]), None)
        assert cov is not None and cov["ok"] is True


class TestReview:
    def test_review_returns_200_list(self, client):
        r = client.get("/api/review")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        # When present, every item carries the console ReviewItem shape.
        for it in body:
            assert {"id", "action", "target_url", "verdict", "raised_by", "ts"} <= set(it)


class TestApiKeys:
    def test_api_keys_returns_200_list_without_secrets(self, client):
        r = client.get("/api/api-keys")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        for k in body:
            assert {"id", "name", "prefix", "last4", "scope", "active"} <= set(k)
            # Never expose secret material.
            assert "secret" not in k and "secret_hash" not in k
            assert k["scope"] in {"read", "read_write", "admin"}


class TestAdminAgents:
    def test_agents_enumerate_real_registry(self, client):
        r = client.get("/api/admin/agents")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list) and body  # registry is non-empty
        names = {a["name"] for a in body}
        # Real agent classes from src.agents.agents.
        assert "takedown_agent" in names
        for a in body:
            assert {"id", "name", "tenant", "running", "runs_today",
                    "budget_usd", "spent_usd"} <= set(a)
            assert a["spent_usd"] <= a["budget_usd"]


class TestAdminUsers:
    def test_users_returns_200_list(self, client):
        r = client.get("/api/admin/users")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        for u in body:
            assert {"id", "email", "role", "mfa_enabled", "last_active"} <= set(u)
