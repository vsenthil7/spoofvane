"""
Tenant and API key administration endpoints.

These routes are mounted under ``/api/admin/`` and require the ``admin:*``
scope. They cover:

* POST /api/admin/tenants — create a new tenant
* GET  /api/admin/tenants — list tenants
* GET  /api/admin/tenants/{id} — fetch one
* POST /api/admin/tenants/{id}/keys — issue a new API key for a tenant
* GET  /api/admin/tenants/{id}/keys — list keys
* DELETE /api/admin/keys/{key_id} — revoke a key
* GET  /api/admin/tenants/{id}/costs — current-day spend with breakdown
* GET  /api/admin/audit-log — recent audit entries
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..common.ids import brand_id as gen_id
from ..common.tenants import (
    ALL_SCOPES,
    SCOPE_ADMIN,
    Tenant,
    TenantPlan,
)
from ..storage.db import session_scope
from ..storage.repositories_v2 import (
    ApiKeyRepo,
    AuditLogRepo,
    CostEventRepo,
    TenantRepo,
)
from .auth import AuthCtx, require_auth

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    plan: TenantPlan = TenantPlan.TRIAL
    daily_spend_cap_usd: float | None = None
    daily_inspect_cap: int | None = None


class ApiKeyIssue(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scopes: list[str] = Field(default_factory=list)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


# --------------------------------------------------------------------------- #
# Tenants
# --------------------------------------------------------------------------- #


@router.post("/tenants", status_code=201)
def create_tenant(
    payload: TenantCreate,
    request: Request,
    ctx: AuthCtx = Depends(require_auth(SCOPE_ADMIN)),
) -> dict:
    tenant = Tenant(
        id=gen_id(),
        name=payload.name,
        plan=payload.plan,
        daily_spend_cap_usd=payload.daily_spend_cap_usd,
        daily_inspect_cap=payload.daily_inspect_cap,
    )
    with session_scope() as s:
        if TenantRepo(s).get_by_name(tenant.name):
            raise HTTPException(409, f"Tenant already exists: {tenant.name}")
        saved = TenantRepo(s).create(tenant)
        AuditLogRepo(s).record(
            actor=ctx.actor,
            action="tenant.create",
            tenant_id=saved.id,
            target_kind="tenant",
            target_id=saved.id,
            after=saved.model_dump(mode="json"),
            request_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    return saved.model_dump(mode="json")


@router.get("/tenants")
def list_tenants(ctx: AuthCtx = Depends(require_auth(SCOPE_ADMIN))) -> list[dict]:
    with session_scope() as s:
        rows = TenantRepo(s).list_all()
    return [t.model_dump(mode="json") for t in rows]


@router.get("/tenants/{tenant_id}")
def get_tenant(tenant_id: str, ctx: AuthCtx = Depends(require_auth(SCOPE_ADMIN))) -> dict:
    with session_scope() as s:
        t = TenantRepo(s).get(tenant_id)
    if t is None:
        raise HTTPException(404, f"Tenant not found: {tenant_id}")
    return t.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# API keys
# --------------------------------------------------------------------------- #


@router.post("/tenants/{tenant_id}/keys", status_code=201)
def issue_key(
    tenant_id: str,
    payload: ApiKeyIssue,
    request: Request,
    ctx: AuthCtx = Depends(require_auth(SCOPE_ADMIN)),
) -> dict:
    # Validate scopes
    for scope in payload.scopes:
        if scope not in ALL_SCOPES and not scope.startswith("brand:"):
            raise HTTPException(400, f"Unknown scope: {scope}")
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
        if payload.expires_in_days else None
    )
    with session_scope() as s:
        if TenantRepo(s).get(tenant_id) is None:
            raise HTTPException(404, f"Tenant not found: {tenant_id}")
        key, plaintext = ApiKeyRepo(s).issue(
            tenant_id, payload.name, payload.scopes, expires_at
        )
        AuditLogRepo(s).record(
            actor=ctx.actor,
            action="apikey.issue",
            tenant_id=tenant_id,
            target_kind="api_key",
            target_id=key.id,
            after={"id": key.id, "name": key.name, "scopes": key.scopes,
                   "expires_at": key.expires_at.isoformat() if key.expires_at else None},
            request_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    return {
        "id": key.id,
        "name": key.name,
        "scopes": key.scopes,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "secret": plaintext,
        "warning": (
            "Save this secret now. It will never be displayed again. "
            "Use the Authorization header: 'ApiKey <id>:<secret>'."
        ),
    }


@router.get("/tenants/{tenant_id}/keys")
def list_keys(
    tenant_id: str, ctx: AuthCtx = Depends(require_auth(SCOPE_ADMIN))
) -> list[dict]:
    with session_scope() as s:
        keys = ApiKeyRepo(s).list_for_tenant(tenant_id)
    return [
        {
            "id": k.id,
            "name": k.name,
            "scopes": k.scopes,
            "created_at": k.created_at.isoformat(),
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
            "is_active": k.is_active,
        }
        for k in keys
    ]


@router.delete("/keys/{key_id}")
def revoke_key(
    key_id: str,
    request: Request,
    ctx: AuthCtx = Depends(require_auth(SCOPE_ADMIN)),
) -> dict:
    with session_scope() as s:
        key = ApiKeyRepo(s).get_by_id(key_id)
        if key is None:
            raise HTTPException(404, f"Key not found: {key_id}")
        ApiKeyRepo(s).revoke(key_id)
        AuditLogRepo(s).record(
            actor=ctx.actor,
            action="apikey.revoke",
            tenant_id=key.tenant_id,
            target_kind="api_key",
            target_id=key_id,
            before={"id": key.id, "scopes": key.scopes},
            request_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    return {"id": key_id, "revoked": True}


# --------------------------------------------------------------------------- #
# Cost attribution
# --------------------------------------------------------------------------- #


@router.get("/tenants/{tenant_id}/costs")
def tenant_costs(
    tenant_id: str,
    days: int = Query(default=1, ge=1, le=90),
    ctx: AuthCtx = Depends(require_auth(SCOPE_ADMIN)),
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with session_scope() as s:
        breakdown = CostEventRepo(s).breakdown_for_tenant(tenant_id, since=since)
        today_total = CostEventRepo(s).total_for_tenant_today(tenant_id)
        tenant = TenantRepo(s).get(tenant_id)
    cap = tenant.daily_spend_cap_usd if tenant else None
    return {
        "tenant_id": tenant_id,
        "today_total_usd": round(today_total, 4),
        "daily_cap_usd": cap,
        "cap_reached": bool(cap is not None and today_total >= cap),
        f"last_{days}_day_breakdown": {k: round(v, 4) for k, v in breakdown.items()},
    }


# --------------------------------------------------------------------------- #
# Audit log
# --------------------------------------------------------------------------- #


@router.get("/audit-log")
def audit_log(
    tenant_id: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    ctx: AuthCtx = Depends(require_auth(SCOPE_ADMIN)),
) -> list[dict]:
    with session_scope() as s:
        return AuditLogRepo(s).list_recent(
            tenant_id=tenant_id, actor=actor, action=action, limit=limit
        )


@router.get("/tuning")
def tuning_report(
    brand_id: str | None = Query(default=None),
    ctx: AuthCtx = Depends(require_auth(SCOPE_ADMIN)),
) -> dict:
    """Active-learning recommendations from captured analyst feedback.

    Returns per-signal precision, a threshold recommendation, and capped
    weight nudges. Advisory only — nothing is applied automatically.
    """
    from ..scoring.active_learning import analyse_feedback
    with session_scope() as s:
        report = analyse_feedback(s, brand_id=brand_id)
    return {
        "brand_id": report.brand_id,
        "sample_size": report.sample_size,
        "sufficient_data": report.sufficient_data,
        "notes": report.notes,
        "signal_precision": [
            {
                "signal_kind": sp.signal_kind,
                "value": sp.value,
                "true_positives": sp.true_positives,
                "false_positives": sp.false_positives,
                "precision": sp.precision,
            }
            for sp in report.signal_precision
        ],
        "threshold": (
            {
                "current": report.threshold.current_threshold,
                "recommended": report.threshold.recommended_threshold,
                "rationale": report.threshold.rationale,
                "tp_mean_score": report.threshold.tp_mean_score,
                "fp_mean_score": report.threshold.fp_mean_score,
                "sample_size": report.threshold.sample_size,
            }
            if report.threshold else None
        ),
        "weight_nudges": [
            {
                "signal": wn.signal,
                "direction": wn.direction,
                "rationale": wn.rationale,
                "suggested_nudge": wn.suggested_nudge,
            }
            for wn in report.weight_nudges
        ],
    }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _client_ip(request: Request) -> str | None:
    # X-Forwarded-For (when behind a reverse proxy) or direct client
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None
