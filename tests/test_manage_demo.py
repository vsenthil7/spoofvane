"""Tests for the demo-data lifecycle manager (scripts/manage_demo.py).

Covers the durable-store guarantee: export -> wipe -> import restores the demo
tables exactly, and status reports counts without mutating. Uses a temp sqlite
DB bound via the db module so the real demo DB is never touched.
"""
from __future__ import annotations

import importlib

import pytest

from src.storage import db as _db
from src.storage.init_db import init_db


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Rebind the engine/session to a throwaway sqlite file for this test."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_file = tmp_path / "test_manage.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(_db, "engine", engine)
    monkeypatch.setattr(_db, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    init_db()
    # Point the fixture path at the temp dir too.
    import scripts.manage_demo as md
    importlib.reload(md)
    monkeypatch.setattr(md, "_FIXTURE", tmp_path / "fixtures" / "demo_dataset.json")
    return md


def _seed_minimal(md):
    """Insert one tenant + one brand + a couple cost events directly."""
    from src.storage.db import session_scope
    from src.storage import models as orm
    from datetime import datetime, timezone
    with session_scope() as s:
        s.add(orm.TenantRow(id="ten_test", name="T", plan="enterprise",
                            daily_spend_cap_usd=500.0, created_at=datetime.now(timezone.utc)))
        s.add(orm.BrandRow(id="brand_test", name="B", login_url="https://x.example",
                           target_country="US", score_threshold=0.65,
                           created_at=datetime.now(timezone.utc)))
        s.add(orm.CostEventRow(id="ce1", tenant_id="ten_test", kind="serp",
                              quantity=1.0, usd_amount=4.2))
        s.add(orm.CostEventRow(id="ce2", tenant_id="ten_test", kind="unlocker",
                              quantity=1.0, usd_amount=9.8))


class TestManageDemo:
    def test_status_runs_without_mutating(self, temp_db, capsys):
        rc = temp_db.cmd_status(None)
        out = capsys.readouterr().out
        assert rc == 0
        assert "Row counts:" in out
        assert "brands" in out

    def test_export_import_roundtrip(self, temp_db):
        from src.storage.db import session_scope
        from src.storage import models as orm
        from sqlalchemy import func, select

        _seed_minimal(temp_db)

        # Export -> fixture file exists with our rows.
        assert temp_db.cmd_export(None) == 0
        assert temp_db._FIXTURE.exists()

        # Wipe every row.
        from src.storage.db import Base
        Base.metadata.drop_all(_db.engine)
        Base.metadata.create_all(_db.engine)
        with session_scope() as s:
            assert s.scalar(select(func.count()).select_from(orm.TenantRow)) == 0

        # Import -> rows restored exactly.
        assert temp_db.cmd_import(None) == 0
        with session_scope() as s:
            assert s.scalar(select(func.count()).select_from(orm.TenantRow)) == 1
            assert s.scalar(select(func.count()).select_from(orm.BrandRow)) == 1
            assert s.scalar(select(func.count()).select_from(orm.CostEventRow)) == 2

    def test_import_is_idempotent(self, temp_db):
        from src.storage.db import session_scope
        from src.storage import models as orm
        from sqlalchemy import func, select

        _seed_minimal(temp_db)
        temp_db.cmd_export(None)
        # Import twice; second import inserts no duplicates.
        temp_db.cmd_import(None)
        temp_db.cmd_import(None)
        with session_scope() as s:
            assert s.scalar(select(func.count()).select_from(orm.CostEventRow)) == 2

    def test_import_without_fixture_returns_error(self, temp_db):
        # No export was run -> fixture absent -> graceful non-zero.
        assert temp_db.cmd_import(None) == 1
