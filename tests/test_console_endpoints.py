"""HTTP tests for the console-facing read surfaces consumed by the Flutter SOC
console: /api/clusters, /api/deepfakes, /api/cost.

These shape existing domain data (alerts + verdicts + scoring + cost events)
into the flat objects the console renders. The tests assert each endpoint
returns 200 with the documented shape, so the Clusters / Deepfakes / Cost
screens can run on LIVE backend data instead of the offline seed lane.
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


class TestConsoleEndpoints:
    def test_deepfakes_returns_list_of_alert_shape(self, client):
        r = client.get("/api/deepfakes")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        # Every row must carry the console Alert keys (shape contract).
        for row in body:
            assert {"id", "brand_id", "url", "verdict", "composite_score"} <= set(row)
            # Only deepfake-family alerts are returned.
            assert (row.get("family") or "").lower() in {
                "deepfake", "deepfake_rtc", "voice_clone", "voice-clone", "synthetic_media"
            }

    def test_clusters_returns_cluster_shape(self, client):
        r = client.get("/api/clusters")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        for c in body:
            assert {"id", "members", "risk"} <= set(c)
            assert isinstance(c["members"], list)
            assert 0.0 <= c["risk"] <= 1.0

    def test_cost_returns_costrow_shape(self, client):
        r = client.get("/api/cost")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        for row in body:
            assert {"product", "usd"} <= set(row)
            assert isinstance(row["usd"], (int, float))

    def test_cost_respects_days_bounds(self, client):
        assert client.get("/api/cost?days=0").status_code == 422
        assert client.get("/api/cost?days=200").status_code == 422
        assert client.get("/api/cost?days=30").status_code == 200

    def test_clusters_limit_bounds(self, client):
        assert client.get("/api/clusters?limit=0").status_code == 422
        assert client.get("/api/clusters?limit=5").status_code == 200
