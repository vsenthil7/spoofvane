"""Create the DB schema from the ORM models.

Run with ``python -m src.storage.init_db``.
"""
from __future__ import annotations

from .db import Base, engine
from . import models  # noqa: F401  (ensure models are registered with Base)
from ..common.logging import get_logger

log = get_logger(__name__)


def init_db() -> None:
    log.info("creating tables")
    Base.metadata.create_all(engine)
    log.info("schema ready", url=engine.url.render_as_string(hide_password=True))


if __name__ == "__main__":
    init_db()
