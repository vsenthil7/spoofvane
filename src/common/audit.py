"""Audit service — tamper-evident, queryable record of every action.

Every state-changing operation (login, brand create, triage, review decision,
takedown submit, member change, report generation) is recorded here with the
actor, account, target, before/after snapshot, request IP/UA, and outcome.

Tamper evidence: each row stores ``prev_hash`` (the previous row's ``row_hash``
for that account) and its own ``row_hash`` = SHA-256 over the canonical
content + prev_hash. Altering or deleting any historical row breaks the chain,
which :func:`verify_chain` detects.

This is the engine behind REQ-AUD-01..05.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from .. import storage as _storage_pkg  # noqa: F401 (namespace marker)
from ..common.ids import make_id
from ..common.logging import get_logger
from ..storage import models as orm

log = get_logger(__name__)

_GENESIS = "0" * 64


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _compute_hash(*, prev_hash: str, content: dict[str, Any]) -> str:
    return hashlib.sha256((prev_hash + _canonical(content)).encode("utf-8")).hexdigest()


def _latest_hash(s: Session, account_id: str | None) -> str:
    """Latest row_hash for this account's chain (prev_hash links per-account)."""
    q = (
        select(orm.AuditLogRow.row_hash)
        .where(orm.AuditLogRow.tenant_id == account_id)
        .order_by(desc(orm.AuditLogRow.seq))
        .limit(1)
    )
    return s.scalar(q) or _GENESIS


def _next_seq(s: Session) -> int:
    """Next GLOBAL monotonic sequence value (the table-wide ordering key).

    Global (not per-account) so the unique seq never collides and verify_chain
    has one deterministic total order even across tenants.
    """
    cur = s.scalar(select(func.max(orm.AuditLogRow.seq)))
    return (cur or 0) + 1


def record(
    s: Session,
    *,
    actor: str,
    action: str,
    account_id: str | None = None,
    target_kind: str | None = None,
    target_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    request_ip: str | None = None,
    user_agent: str | None = None,
    status_code: int | None = None,
    detail: str | None = None,
) -> str:
    """Append a hash-chained audit entry; returns its row_hash."""
    prev = _latest_hash(s, account_id)
    content = {
        "actor": actor, "action": action, "account_id": account_id,
        "target_kind": target_kind, "target_id": target_id,
        "before": before, "after": after, "status_code": status_code,
        "detail": detail, "request_ip": request_ip,
    }
    row_hash = _compute_hash(prev_hash=prev, content=content)
    row = orm.AuditLogRow(
        id=make_id("audit"),
        seq=_next_seq(s),
        tenant_id=account_id,
        actor=actor,
        action=action,
        target_kind=target_kind,
        target_id=target_id,
        before_json=before,
        after_json=after,
        request_ip=request_ip,
        user_agent=user_agent,
        status_code=status_code,
        detail=detail,
        prev_hash=prev,
        row_hash=row_hash,
    )
    s.add(row)
    s.flush()
    return row_hash


def verify_chain(s: Session, account_id: str | None = None) -> dict[str, Any]:
    """Recompute the chain and report the first break, if any."""
    q = select(orm.AuditLogRow).order_by(orm.AuditLogRow.seq)
    if account_id is not None:
        q = q.where(orm.AuditLogRow.tenant_id == account_id)
    rows = list(s.scalars(q).all())
    # prev_hash links per-account, so track a cursor per account even when
    # verifying the whole table (rows interleave across tenants by global seq).
    prev_by_acct: dict[str | None, str] = {}
    for i, r in enumerate(rows):
        content = {
            "actor": r.actor, "action": r.action, "account_id": r.tenant_id,
            "target_kind": r.target_kind, "target_id": r.target_id,
            "before": r.before_json, "after": r.after_json,
            "status_code": r.status_code, "detail": r.detail,
            "request_ip": r.request_ip,
        }
        prev = prev_by_acct.get(r.tenant_id, _GENESIS)
        expected = _compute_hash(prev_hash=prev, content=content)
        if r.prev_hash != prev or r.row_hash != expected:
            return {
                "valid": False, "verified": i, "total": len(rows),
                "broken_at": r.id, "broken_index": i,
            }
        prev_by_acct[r.tenant_id] = r.row_hash
    return {"valid": True, "verified": len(rows), "total": len(rows)}


def query(
    s: Session,
    *,
    account_id: str | None = None,
    actor: str | None = None,
    action: str | None = None,
    target_kind: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 200,
) -> list[dict]:
    q = select(orm.AuditLogRow).order_by(desc(orm.AuditLogRow.created_at)).limit(limit)
    if account_id:
        q = q.where(orm.AuditLogRow.tenant_id == account_id)
    if actor:
        q = q.where(orm.AuditLogRow.actor == actor)
    if action:
        q = q.where(orm.AuditLogRow.action == action)
    if target_kind:
        q = q.where(orm.AuditLogRow.target_kind == target_kind)
    if since:
        q = q.where(orm.AuditLogRow.created_at >= since)
    if until:
        q = q.where(orm.AuditLogRow.created_at <= until)
    rows = s.scalars(q).all()
    return [_row_dict(r) for r in rows]


def _row_dict(r: orm.AuditLogRow) -> dict:
    created = r.created_at
    if created and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return {
        "id": r.id, "account_id": r.tenant_id, "actor": r.actor,
        "action": r.action, "target_kind": r.target_kind, "target_id": r.target_id,
        "before": r.before_json, "after": r.after_json,
        "status_code": r.status_code, "detail": r.detail,
        "request_ip": r.request_ip, "user_agent": r.user_agent,
        "row_hash": r.row_hash, "prev_hash": r.prev_hash,
        "created_at": created.isoformat() if created else None,
    }


def export_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    cols = ["created_at", "actor", "action", "target_kind", "target_id",
            "status_code", "request_ip", "detail", "row_hash"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue()


def export_json(rows: list[dict]) -> str:
    return json.dumps(rows, indent=2, default=str)


__all__ = ["record", "verify_chain", "query", "export_csv", "export_json"]
