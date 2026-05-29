"""
Shared pytest fixtures.

Each test session gets its own temp database and evidence directory, so tests
don't interfere with the demo database the user may already have populated
via ``scripts/seed_demo.py``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Force mock mode before any src import.
os.environ["MOCK_MODE"] = "true"


@pytest.fixture(scope="session", autouse=True)
def _isolate_storage(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Point the app at a session-scoped tmp dir for DB + evidence + reports.

    We mutate the env before ``get_settings()`` is first called, and also
    clear the lru_cache afterwards in case some import path called it
    earlier.
    """
    root = tmp_path_factory.mktemp("spoofvane")
    db_path = root / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["EVIDENCE_DIR"] = str(root / "evidence")
    os.environ["REPORTS_DIR"] = str(root / "reports")
    os.environ["CANONICAL_DIR"] = str(root / "canonical")

    from src.common import settings as settings_mod

    settings_mod.get_settings.cache_clear()  # type: ignore[attr-defined]

    # Re-bind the engine / SessionLocal to the new URL, because db.py
    # captured the old one at import time.
    from src.storage import db as db_mod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_mod.engine = create_engine(
        os.environ["DATABASE_URL"], future=True, connect_args={"check_same_thread": False}
    )
    db_mod.SessionLocal = sessionmaker(
        bind=db_mod.engine, autocommit=False, autoflush=False, future=True
    )

    # Create schema
    from src.storage.init_db import init_db

    init_db()

    yield root
