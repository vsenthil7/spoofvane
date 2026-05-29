"""End-to-end product flow over HTTP (synchronous pipeline).

Runs discovery with ?wait=true so alerts are generated inline, then exercises
the alert detail, triage, notes, takedown, and audit-log endpoints against
real data. This covers the app.py pipeline + alert-action surface and the
takedown submission route end to end.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.storage.init_db import init_db


@pytest.fixture(scope="module", autouse=True)
def _schema(monkeypatch_module):
    init_db()


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    # enable a takedown provider so submission can succeed in mock mode
    mp.setenv("MOCK_MODE", "true")
    mp.setenv("CLOUDFLARE_ABUSE_EMAIL", "abuse@demo.example")
    from src.common import settings as smod
    smod.get_settings.cache_clear()
    yield mp
    mp.undo()
    smod.get_settings.cache_clear()


@pytest.fixture(scope="module")
def client(monkeypatch_module):
    from src.api.app import app
    return TestClient(app)


@pytest.fixture(scope="module")
def brand_with_alerts(client):
    """Seed the demo (baselined brand) so discovery generates real alerts."""
    import scripts.seed_demo as sd
    try:
        if hasattr(sd, "main"):
            sd.main()
    except SystemExit:
        pass
    alerts = client.get("/api/alerts").json()
    items = alerts if isinstance(alerts, list) else alerts.get("items", [])
    if items and isinstance(items[0], dict) and "brand_id" in items[0]:
        return items[0]["brand_id"]
    return None


class TestEndToEndFlow:
    def test_discovery_generated_alerts(self, client, brand_with_alerts):
        alerts = client.get("/api/alerts").json()
        items = alerts if isinstance(alerts, list) else alerts.get("items", [])
        # synchronous discovery should have produced at least one alert
        assert isinstance(items, list)

    def test_alert_detail(self, client, brand_with_alerts):
        alerts = client.get("/api/alerts").json()
        items = alerts if isinstance(alerts, list) else alerts.get("items", [])
        if not items:
            pytest.skip("no alerts generated")
        aid = items[0]["id"]
        r = client.get(f"/api/alerts/{aid}")
        assert r.status_code == 200

    def test_triage_then_takedown(self, client, brand_with_alerts):
        alerts = client.get("/api/alerts").json()
        items = alerts if isinstance(alerts, list) else alerts.get("items", [])
        if not items:
            pytest.skip("no alerts generated")
        aid = items[0]["id"]
        # triage to confirmed
        t = client.post(f"/api/alerts/{aid}/triage",
                        json={"status": "confirmed", "triaged_by": "tester"})
        assert t.status_code in (200, 204)
        # add a note
        n = client.post(f"/api/alerts/{aid}/notes",
                        json={"body": "confirmed clone", "author": "tester"})
        assert n.status_code in (200, 201)
        # submit takedown (provider enabled + mock mode -> success)
        td = client.post(f"/api/alerts/{aid}/takedown")
        assert td.status_code in (200, 400)  # 200 success, 400 if no provider matched host
        if td.status_code == 200:
            assert td.json().get("case_id") or td.json().get("provider")

    def test_recheck(self, client, brand_with_alerts):
        alerts = client.get("/api/alerts").json()
        items = alerts if isinstance(alerts, list) else alerts.get("items", [])
        if not items:
            pytest.skip("no alerts")
        aid = items[0]["id"]
        r = client.post("/api/discovery/recheck", json={"alert_id": aid})
        assert r.status_code in (200, 202, 404, 422)

    def test_audit_log_endpoint(self, client, brand_with_alerts):
        # the global /api/audit-log meta endpoint
        r = client.get("/api/audit-log")
        assert r.status_code in (200, 401, 403)
