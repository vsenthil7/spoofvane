"""Create the DB schema from the ORM models.

Run with ``python -m src.storage.init_db``.
"""
from __future__ import annotations

from . import db as _db
from .db import Base
from . import models  # noqa: F401  (ensure models are registered with Base)
from . import identity_models  # noqa: F401  (v0.3 identity/HITL/notifications/reports)
from ..common.logging import get_logger

log = get_logger(__name__)


def init_db() -> None:
    log.info("creating tables")
    # Read the engine off the module at call time, so test harnesses that
    # rebind ``db.engine`` to a temp database are honoured.
    engine = _db.engine
    Base.metadata.create_all(engine)
    log.info("schema ready", url=engine.url.render_as_string(hide_password=True))


if __name__ == "__main__":
    init_db()
