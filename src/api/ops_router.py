"""Operations router — review (HITL), notifications, reports, audit.

All routes are RBAC-gated via the dependencies in :mod:`deps`. Account scoping
is taken from the authenticated user, never from the request body, so one
account can never read or act on another's data.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from ..common import audit, notifications, reports, review
from ..common.rbac import Permission
from ..storage.db import session_scope
from .deps import AuthedUser, current_user, require

router = APIRouter(prefix="/api", tags=["ops"])


# ─────────────────────────── Review (HITL) ──────────────────────────────

class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(approve|reject|escalate)$")
    human_verdict: str | None = None
    reason: str | None = None


@router.get("/review/queue")
async def review_queue(
    state: str = "pending",
    user: AuthedUser = Depends(require(Permission.REVIEW_READ)),
) -> dict:
    with session_scope() as s:
        items = review.list_queue(s, account_id=user.account_id, state=state)
        stats = review.queue_stats(s, account_id=user.account_id)
    return {"items": items, "stats": stats}


@router.post("/review/{review_id}/decide")
async def review_decide(
    review_id: str, body: DecisionIn, request: Request,
    user: AuthedUser = Depends(require(Permission.REVIEW_DECIDE)),
) -> dict:
    with session_scope() as s:
        try:
            result = review.decide(
                s, review_id=review_id, decision=body.decision,
                decided_by=user.user_id, actor_email=user.email,
                human_verdict=body.human_verdict, reason=body.reason,
                request_ip=request.client.host if request.client else None,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return result


class AssignIn(BaseModel):
    assignee_user_id: str


@router.post("/review/{review_id}/assign")
async def review_assign(
    review_id: str, body: AssignIn,
    user: AuthedUser = Depends(require(Permission.ALERTS_ASSIGN)),
) -> dict:
    with session_scope() as s:
        try:
            review.assign(s, review_id=review_id,
                          assignee_user_id=body.assignee_user_id, actor_email=user.email)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True}


# ─────────────────────────── Notifications ──────────────────────────────

@router.get("/notifications")
async def list_notifications(
    unread_only: bool = False,
    user: AuthedUser = Depends(current_user),
) -> dict:
    with session_scope() as s:
        items = notifications.list_for_user(
            s, user_id=user.user_id, account_id=user.account_id, unread_only=unread_only
        )
    return {"items": items}


@router.post("/notifications/{notification_id}/read")
async def read_notification(
    notification_id: str, user: AuthedUser = Depends(current_user),
) -> dict:
    with session_scope() as s:
        notifications.mark_read(s, notification_id=notification_id)
    return {"ok": True}


class PrefIn(BaseModel):
    kind: str
    in_app: bool = True
    email: bool = True
    min_severity: str = Field(default="info", pattern="^(info|warning|critical)$")


@router.post("/notifications/prefs")
async def set_pref(
    body: PrefIn,
    user: AuthedUser = Depends(require(Permission.NOTIFICATIONS_MANAGE)),
) -> dict:
    with session_scope() as s:
        notifications.set_pref(
            s, user_id=user.user_id, account_id=user.account_id, kind=body.kind,
            in_app=body.in_app, email=body.email, min_severity=body.min_severity,
        )
    return {"ok": True}


# ─────────────────────────────── Reports ────────────────────────────────

@router.post("/reports/{kind}")
async def generate_report(
    kind: str, fmt: str = Query("pdf", pattern="^(pdf|csv|json)$"),
    user: AuthedUser = Depends(require(Permission.REPORTS_GENERATE)),
) -> dict:
    with session_scope() as s:
        if kind == "detection_summary":
            path = reports.generate_detection_summary(
                s, account_id=user.account_id, fmt=fmt, generated_by=user.user_id)
        elif kind == "board_pack":
            path = reports.generate_board_pack(
                s, account_id=user.account_id, generated_by=user.user_id)
        elif kind == "audit_export":
            path = reports.generate_audit_export(
                s, account_id=user.account_id, fmt=fmt if fmt != "pdf" else "csv",
                generated_by=user.user_id)
        else:
            raise HTTPException(status_code=404, detail=f"unknown report kind: {kind}")
    return {"path": path, "kind": kind, "fmt": fmt}


@router.get("/reports")
async def list_reports(user: AuthedUser = Depends(require(Permission.REPORTS_READ))) -> dict:
    with session_scope() as s:
        return {"items": reports.list_reports(s, account_id=user.account_id)}


# ───────────────────────────────── Audit ────────────────────────────────

@router.get("/audit")
async def query_audit(
    actor: str | None = None, action: str | None = None, limit: int = 200,
    user: AuthedUser = Depends(require(Permission.AUDIT_READ)),
) -> dict:
    with session_scope() as s:
        rows = audit.query(s, account_id=user.account_id, actor=actor,
                           action=action, limit=limit)
        chain = audit.verify_chain(s, account_id=user.account_id)
    return {"entries": rows, "chain_verification": chain}


@router.get("/audit/verify")
async def verify_audit(user: AuthedUser = Depends(require(Permission.AUDIT_READ))) -> dict:
    with session_scope() as s:
        return audit.verify_chain(s, account_id=user.account_id)


@router.get("/audit/export")
async def export_audit(
    fmt: str = Query("csv", pattern="^(csv|json)$"),
    user: AuthedUser = Depends(require(Permission.AUDIT_EXPORT)),
):
    with session_scope() as s:
        rows = audit.query(s, account_id=user.account_id, limit=10000)
        body = audit.export_csv(rows) if fmt == "csv" else audit.export_json(rows)
    media = "text/csv" if fmt == "csv" else "application/json"
    return PlainTextResponse(body, media_type=media)


# ─────────────────────────── AI Triage Copilot ──────────────────────────

class CopilotAsk(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    brand_id: str | None = None
    # When True the analyst is asking the agent to also be able to move triage
    # state. This requires the stronger ALERTS_TRIAGE permission (enforced in
    # the route), and even then the agent can never approve/send a takedown.
    allow_actions: bool = False


@router.post("/copilot/ask")
async def copilot_ask(
    body: CopilotAsk,
    user: AuthedUser = Depends(require(Permission.ALERTS_READ)),
) -> dict:
    """Ask the agentic AI Triage Copilot a natural-language question.

    Read-only by default. If ``allow_actions`` is requested, the caller must
    additionally hold ``ALERTS_TRIAGE``; the agent can then move triage state
    but never approve or submit a takedown — that gate stays in the review
    queue.
    """
    from ..verdict.copilot import get_triage_copilot
    from ..common.rbac import permissions_for

    if body.allow_actions and Permission.ALERTS_TRIAGE not in permissions_for(user.role):
        raise HTTPException(
            status_code=403,
            detail="allow_actions requires the alerts:triage permission",
        )

    copilot = get_triage_copilot(allow_actions=body.allow_actions)
    result = copilot.ask(body.question, brand_id=body.brand_id)
    return {
        "answer": result.answer,
        "model_used": result.model_used,
        "iterations": result.iterations,
        "steps": [
            {"tool": st.tool, "arguments": st.arguments, "ok": st.ok}
            for st in result.steps
        ],
    }


__all__ = ["router"]
