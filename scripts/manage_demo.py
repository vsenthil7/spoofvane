"""
Demo data lifecycle manager for SpoofVane.

One script to create, inspect, reset, and fully regenerate the demo dataset, so
the demo data is never lost across updates and can always be rebuilt from
scratch. The seed itself lives in ``scripts.seed_demo`` (brand + pipeline pass +
tenant + Bright Data cost events); this wrapper adds safe lifecycle commands.

Usage::

    python -m scripts.manage_demo status     # counts per table (no changes)
    python -m scripts.manage_demo seed        # idempotent: ensure demo data exists
    python -m scripts.manage_demo reset        # wipe ALL rows, recreate schema, re-seed
    python -m scripts.manage_demo reset --no-seed   # wipe + recreate schema only
    python -m scripts.manage_demo nuke --yes  # delete the sqlite db file entirely

Safety:
* ``reset`` and ``nuke`` are destructive and require ``--yes`` unless stdin is a
  TTY (then they prompt). They never run silently from automation without --yes.
* ``seed`` is always safe + idempotent.
* A timestamped backup of the sqlite file is taken before any destructive op
  (``data/backups/spoofvane-<ts>.db``), so a demo dataset is recoverable.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from src.common.logging import get_logger
from src.common.settings import get_settings
from src.storage import db as _db
from src.storage.db import Base, session_scope
from src.storage.init_db import init_db
from src.storage import models as orm

log = get_logger(__name__)


# Tables worth counting in `status` (label -> ORM row class attribute name).
_COUNT_TABLES = [
    ("brands", "BrandRow"),
    ("suspect_urls", "SuspectURLRow"),
    ("inspections", "InspectionRow"),
    ("alerts", "AlertRow"),
    ("tenants", "TenantRow"),
    ("cost_events", "CostEventRow"),
    ("audit_log", "AuditLogRow"),
]


def _db_file() -> Path | None:
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        return Path(url.replace("sqlite:///", "", 1))
    return None


def _backup_db() -> Path | None:
    """Copy the sqlite file to data/backups/ before a destructive op."""
    f = _db_file()
    if f is None or not f.exists():
        return None
    backups = f.parent / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest = backups / f"spoofvane-{ts}.db"
    shutil.copy2(f, dest)
    log.info("manage.backup", path=str(dest))
    return dest


def _count(label: str, row_attr: str) -> int:
    row_cls = getattr(orm, row_attr, None)
    if row_cls is None:
        return -1
    try:
        with session_scope() as s:
            return int(s.scalar(select(func.count()).select_from(row_cls)) or 0)
    except Exception:  # table may not exist yet
        return -1


def cmd_status(_args) -> int:
    f = _db_file()
    print(f"DB: {f} ({'exists' if f and f.exists() else 'absent'})")
    print("Row counts:")
    for label, attr in _COUNT_TABLES:
        n = _count(label, attr)
        print(f"  {label:<14} {'(no table)' if n < 0 else n}")
    return 0


def _confirm(action: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print(f"Refusing to {action} without --yes (non-interactive).")
        return False
    return input(f"Really {action}? [y/N] ").strip().lower() in {"y", "yes"}


def cmd_reset(args) -> int:
    if not _confirm("wipe ALL data and recreate the schema", args.yes):
        return 1
    _backup_db()
    engine = _db.engine
    log.info("manage.reset.drop_all")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("✓ Schema recreated (all rows dropped).")
    if not args.no_seed:
        import scripts.seed_demo as seed_demo
        seed_demo.main()
        print("✓ Re-seeded demo data.")
    return 0


def cmd_seed(_args) -> int:
    import scripts.seed_demo as seed_demo
    return seed_demo.main()


def cmd_nuke(args) -> int:
    if not _confirm("DELETE the database file", args.yes):
        return 1
    f = _db_file()
    if f is None:
        print("Database is not a sqlite file; nothing to delete.")
        return 1
    _backup_db()
    if f.exists():
        f.unlink()
        print(f"✓ Deleted {f}")
    else:
        print("Database file already absent.")
    return 0


# Committed, version-controlled snapshot of the demo dataset. Unlike the binary
# sqlite file (gitignored), this JSON fixture is checked in so the exact demo
# data is never lost and can be restored deterministically after a reset.
_FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "demo_dataset.json"

# (label, ORM row attr) for tables exported/imported as the durable demo set.
_SNAPSHOT_TABLES = [
    ("tenants", "TenantRow"),
    ("brands", "BrandRow"),
    ("cost_events", "CostEventRow"),
]

# Only these cost-event kinds are part of the durable demo fixture. Per-run
# pipeline cost noise (e.g. browser_minute, one per inspected URL) is excluded
# so the committed fixture stays small and stable across re-seeds.
_DEMO_COST_KINDS = {
    "serp", "unlocker", "scraping_browser",
    "residential", "web_scraper", "datasets",
}


def _row_to_dict(row) -> dict:
    out = {}
    for col in row.__table__.columns:
        v = getattr(row, col.name)
        if isinstance(v, datetime):
            v = v.isoformat()
        out[col.name] = v
    return out


def cmd_export(_args) -> int:
    """Serialize the durable demo tables to the committed JSON fixture."""
    _FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    snapshot: dict[str, list[dict]] = {}
    with session_scope() as s:
        for label, attr in _SNAPSHOT_TABLES:
            row_cls = getattr(orm, attr)
            rows = s.scalars(select(row_cls)).all()
            dicts = [_row_to_dict(r) for r in rows]
            # Keep only the durable named demo cost kinds; drop per-run noise.
            if label == "cost_events":
                dicts = [d for d in dicts if d.get("kind") in _DEMO_COST_KINDS]
            snapshot[label] = dicts
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tables": snapshot,
    }
    _FIXTURE.write_text(json.dumps(payload, indent=2, default=str))
    counts = {k: len(v) for k, v in snapshot.items()}
    print(f"✓ Exported demo fixture -> {_FIXTURE}")
    print(f"  {counts}")
    return 0


def cmd_import(_args) -> int:
    """Restore the durable demo tables from the committed JSON fixture.
    Insert-or-skip by primary key, so it is safe to run repeatedly."""
    if not _FIXTURE.exists():
        print(f"No fixture at {_FIXTURE}; run `export` first or use `seed`.")
        return 1
    init_db()
    payload = json.loads(_FIXTURE.read_text())
    tables = payload.get("tables", {})
    inserted = {}
    with session_scope() as s:
        for label, attr in _SNAPSHOT_TABLES:
            row_cls = getattr(orm, attr)
            pk_cols = [c.name for c in row_cls.__table__.primary_key.columns]
            n = 0
            for rowdict in tables.get(label, []):
                pk = {k: rowdict[k] for k in pk_cols}
                if s.get(row_cls, tuple(pk.values()) if len(pk) > 1 else next(iter(pk.values()))):
                    continue  # already present
                # Coerce ISO datetime strings back to datetime for DateTime cols.
                clean = {}
                for col in row_cls.__table__.columns:
                    val = rowdict.get(col.name)
                    if val is not None and str(col.type).startswith("DATETIME") and isinstance(val, str):
                        try:
                            val = datetime.fromisoformat(val)
                        except ValueError:
                            pass
                    clean[col.name] = val
                s.add(row_cls(**clean))
                n += 1
            inserted[label] = n
    print(f"✓ Imported demo fixture from {_FIXTURE}")
    print(f"  inserted (new rows): {inserted}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="manage_demo", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="print row counts (no changes)").set_defaults(func=cmd_status)
    sub.add_parser("seed", help="ensure demo data exists (idempotent)").set_defaults(func=cmd_seed)

    r = sub.add_parser("reset", help="wipe all rows, recreate schema, re-seed")
    r.add_argument("--yes", action="store_true", help="skip confirmation")
    r.add_argument("--no-seed", action="store_true", help="recreate schema only, do not re-seed")
    r.set_defaults(func=cmd_reset)

    n = sub.add_parser("nuke", help="delete the sqlite db file")
    n.add_argument("--yes", action="store_true", help="skip confirmation")
    n.set_defaults(func=cmd_nuke)

    sub.add_parser(
        "export", help="write durable demo tables to the committed JSON fixture"
    ).set_defaults(func=cmd_export)
    sub.add_parser(
        "import", help="restore durable demo tables from the committed JSON fixture"
    ).set_defaults(func=cmd_import)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Ensure schema exists for status/seed (safe no-op if already there).
    if args.cmd in {"status", "seed"}:
        init_db()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
