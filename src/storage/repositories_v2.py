"""
Repositories for the v0.2 platform tables:
* Tenants and API keys
* Cost-attribution events
* Active-learning feedback events
* Audit log
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..common import models as m
from ..common import tenants as t
from ..common.ids import alert_id
from . import models as orm
from .repositories import _to_utc


# --------------------------------------------------------------------------- #
# Tenants
# --------------------------------------------------------------------------- #


class TenantRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def create(self, tenant: t.Tenant) -> t.Tenant:
        row = orm.TenantRow(
            id=tenant.id,
            name=tenant.name,
            plan=tenant.plan.value,
            daily_spend_cap_usd=tenant.daily_spend_cap_usd,
            daily_inspect_cap=tenant.daily_inspect_cap,
            created_at=tenant.created_at,
        )
        self.s.add(row)
        self.s.flush()
        return tenant

    def get(self, tenant_id: str) -> t.Tenant | None:
        row = self.s.get(orm.TenantRow, tenant_id)
        return self._to_pydantic(row) if row else None

    def get_by_name(self, name: str) -> t.Tenant | None:
        row = self.s.scalar(select(orm.TenantRow).where(orm.TenantRow.name == name))
        return self._to_pydantic(row) if row else None

    def list_all(self) -> list[t.Tenant]:
        rows = self.s.scalars(select(orm.TenantRow).order_by(orm.TenantRow.created_at)).all()
        return [self._to_pydantic(r) for r in rows]

    @staticmethod
    def _to_pydantic(row: orm.TenantRow) -> t.Tenant:
        return t.Tenant(
            id=row.id,
            name=row.name,
            plan=t.TenantPlan(row.plan),
            daily_spend_cap_usd=row.daily_spend_cap_usd,
            daily_inspect_cap=row.daily_inspect_cap,
            created_at=_to_utc(row.created_at),
        )


# --------------------------------------------------------------------------- #
# API keys
# --------------------------------------------------------------------------- #


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


class ApiKeyRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def issue(
        self,
        tenant_id: str,
        name: str,
        scopes: Iterable[str],
        expires_at: datetime | None = None,
    ) -> tuple[t.ApiKey, str]:
        """Issue a new key. Returns (api_key_record, plaintext_secret).
        The plaintext secret is only available at this moment — store it
        somewhere the user can retrieve it (1Password, Vault) immediately.
        """
        # Public id: "dd_<16char>". Secret: 32 url-safe chars.
        public_id = "dd_" + secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]
        plaintext_secret = secrets.token_urlsafe(32)
        api_key = t.ApiKey(
            id=public_id,
            tenant_id=tenant_id,
            name=name,
            scopes=list(scopes),
            secret_hash=_hash_secret(plaintext_secret),
            expires_at=expires_at,
        )
        row = orm.ApiKeyRow(
            id=api_key.id,
            tenant_id=api_key.tenant_id,
            name=api_key.name,
            scopes=api_key.scopes,
            secret_hash=api_key.secret_hash,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        )
        self.s.add(row)
        self.s.flush()
        return api_key, plaintext_secret

    def get_by_id(self, key_id: str) -> t.ApiKey | None:
        row = self.s.get(orm.ApiKeyRow, key_id)
        return self._to_pydantic(row) if row else None

    def authenticate(self, key_id: str, plaintext_secret: str) -> t.ApiKey | None:
        """Return the ApiKey iff the secret matches and the key is active."""
        row = self.s.get(orm.ApiKeyRow, key_id)
        if row is None:
            return None
        expected = _hash_secret(plaintext_secret)
        if not secrets.compare_digest(row.secret_hash, expected):
            return None
        api_key = self._to_pydantic(row)
        if not api_key.is_active:
            return None
        # Update last_used_at
        row.last_used_at = datetime.now(timezone.utc)
        self.s.flush()
        return api_key

    def revoke(self, key_id: str) -> bool:
        row = self.s.get(orm.ApiKeyRow, key_id)
        if row is None:
            return False
        row.revoked_at = datetime.now(timezone.utc)
        self.s.flush()
        return True

    def list_for_tenant(self, tenant_id: str) -> list[t.ApiKey]:
        rows = self.s.scalars(
            select(orm.ApiKeyRow)
            .where(orm.ApiKeyRow.tenant_id == tenant_id)
            .order_by(desc(orm.ApiKeyRow.created_at))
        ).all()
        return [self._to_pydantic(r) for r in rows]

    @staticmethod
    def _to_pydantic(row: orm.ApiKeyRow) -> t.ApiKey:
        return t.ApiKey(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            scopes=list(row.scopes or []),
            secret_hash=row.secret_hash,
            last_used_at=_to_utc(row.last_used_at),
            expires_at=_to_utc(row.expires_at),
            revoked_at=_to_utc(row.revoked_at),
            created_at=_to_utc(row.created_at),
        )


# --------------------------------------------------------------------------- #
# Cost-attribution
# --------------------------------------------------------------------------- #


class CostEventRepo:
    """Records each Bright Data API call against a tenant for billing
    transparency and per-tenant budget enforcement."""

    def __init__(self, session: Session) -> None:
        self.s = session

    def record(
        self,
        *,
        kind: str,
        usd_amount: float,
        tenant_id: str | None = None,
        brand_id: str | None = None,
        quantity: float = 1.0,
    ) -> None:
        from ..common.ids import alert_id as _id  # reuse the ULID factory
        row = orm.CostEventRow(
            id=_id(),
            tenant_id=tenant_id,
            brand_id=brand_id,
            kind=kind,
            quantity=quantity,
            usd_amount=usd_amount,
        )
        self.s.add(row)
        self.s.flush()

    def total_for_tenant_today(self, tenant_id: str) -> float:
        from datetime import timedelta
        start_of_day = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        total = self.s.scalar(
            select(func.coalesce(func.sum(orm.CostEventRow.usd_amount), 0.0)).where(
                orm.CostEventRow.tenant_id == tenant_id,
                orm.CostEventRow.occurred_at >= start_of_day,
            )
        )
        return float(total or 0.0)

    def breakdown_for_tenant(
        self, tenant_id: str, since: datetime | None = None
    ) -> dict[str, float]:
        q = select(
            orm.CostEventRow.kind,
            func.coalesce(func.sum(orm.CostEventRow.usd_amount), 0.0),
        ).where(orm.CostEventRow.tenant_id == tenant_id)
        if since is not None:
            q = q.where(orm.CostEventRow.occurred_at >= since)
        q = q.group_by(orm.CostEventRow.kind)
        return {kind: float(amt) for kind, amt in self.s.execute(q).all()}


# --------------------------------------------------------------------------- #
# Active learning — analyst triage feedback
# --------------------------------------------------------------------------- #


class FeedbackEventRepo:
    """Captures analyst triage outcomes (true positive / false positive)
    so we can adjust scoring weights and verdict thresholds over time."""

    def __init__(self, session: Session) -> None:
        self.s = session

    def record(
        self,
        *,
        alert_id: str,
        outcome: str,  # "true_positive" | "false_positive" | "indeterminate"
        actor: str,
        tenant_id: str | None = None,
        brand_id: str | None = None,
        attack_family: str | None = None,
        kit_match: str | None = None,
        cloaking_detected: bool = False,
        composite_score: float | None = None,
        notes: str | None = None,
    ) -> None:
        from ..common.ids import alert_id as _id
        row = orm.FeedbackEventRow(
            id=_id(),
            alert_id=alert_id,
            tenant_id=tenant_id,
            brand_id=brand_id,
            outcome=outcome,
            actor=actor,
            notes=notes,
            attack_family=attack_family,
            kit_match=kit_match,
            cloaking_detected=cloaking_detected,
            composite_score=composite_score,
        )
        self.s.add(row)
        self.s.flush()

    def precision_by_signal(self, signal_kind: str, signal_value: str) -> dict:
        """Return tp/fp counts and precision for a (family|kit|cloaking) value.

        ``signal_kind`` is one of "attack_family", "kit_match", "cloaking".
        """
        col = {
            "attack_family": orm.FeedbackEventRow.attack_family,
            "kit_match": orm.FeedbackEventRow.kit_match,
            "cloaking": orm.FeedbackEventRow.cloaking_detected,
        }.get(signal_kind)
        if col is None:
            return {"signal": signal_kind, "value": signal_value, "tp": 0, "fp": 0, "precision": None}

        if signal_kind == "cloaking":
            cond = col.is_(signal_value.lower() in ("true", "1", "yes"))
        else:
            cond = col == signal_value

        tp = self.s.scalar(
            select(func.count()).where(
                cond, orm.FeedbackEventRow.outcome == "true_positive"
            )
        ) or 0
        fp = self.s.scalar(
            select(func.count()).where(
                cond, orm.FeedbackEventRow.outcome == "false_positive"
            )
        ) or 0
        total = tp + fp
        precision = (tp / total) if total else None
        return {
            "signal": signal_kind,
            "value": signal_value,
            "tp": int(tp),
            "fp": int(fp),
            "precision": precision,
        }


# --------------------------------------------------------------------------- #
# Audit log
# --------------------------------------------------------------------------- #


class AuditLogRepo:
    """Append-only state-change record. Never deleted; queryable for
    compliance and incident investigation."""

    def __init__(self, session: Session) -> None:
        self.s = session

    def record(
        self,
        *,
        actor: str,
        action: str,
        tenant_id: str | None = None,
        target_kind: str | None = None,
        target_id: str | None = None,
        before: dict | None = None,
        after: dict | None = None,
        request_ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        from ..common.ids import alert_id as _id
        row = orm.AuditLogRow(
            id=_id(),
            tenant_id=tenant_id,
            actor=actor,
            action=action,
            target_kind=target_kind,
            target_id=target_id,
            before_json=before,
            after_json=after,
            request_ip=request_ip,
            user_agent=user_agent,
        )
        self.s.add(row)
        self.s.flush()

    def list_recent(
        self,
        tenant_id: str | None = None,
        actor: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        q = select(orm.AuditLogRow).order_by(desc(orm.AuditLogRow.created_at)).limit(limit)
        if tenant_id:
            q = q.where(orm.AuditLogRow.tenant_id == tenant_id)
        if actor:
            q = q.where(orm.AuditLogRow.actor == actor)
        if action:
            q = q.where(orm.AuditLogRow.action == action)
        rows = self.s.scalars(q).all()
        return [
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "actor": r.actor,
                "action": r.action,
                "target_kind": r.target_kind,
                "target_id": r.target_id,
                "before": r.before_json,
                "after": r.after_json,
                "request_ip": r.request_ip,
                "user_agent": r.user_agent,
                "created_at": _to_utc(r.created_at).isoformat() if r.created_at else None,
            }
            for r in rows
        ]
