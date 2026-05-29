"""Human-in-the-loop review — AI proposes, a human disposes.

The detection pipeline never auto-actions a consequential verdict. Instead,
for any verdict at or above the configured severity it enqueues a
:class:`ReviewItemRow` in state ``pending`` with an SLA clock. A user with the
``review:decide`` permission (Reviewer/Admin/Owner) then:

* **approve**  — confirms the AI verdict; an approved ``phish`` becomes eligible
  for takedown submission (the only path to ``takedown:submit``).
* **reject**   — overrides to benign/false-positive; no action taken.
* **escalate** — routes to a senior reviewer / raises severity.

Every decision (a) writes an audit entry, (b) emits a notification, and
(c) feeds the active-learning loop as a labelled outcome. This satisfies
REQ-HITL-01..04 and is the gate enforcing REQ-TKD-02 (no ungated takedown).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..common import audit, notifications
from ..common.ids import make_id
from ..common.logging import get_logger
from ..storage.identity_models import AccountRow, ReviewItemRow

log = get_logger(__name__)

_AUTO_REVIEW_SEVERITIES = {"high", "critical"}  # these always require a human
_DECISIONS = {"approve", "reject", "escalate"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ─────────────────────────── Enqueue (from pipeline) ────────────────────

def enqueue_for_review(
    s: Session,
    *,
    account_id: str,
    alert_id: str,
    suspect_url: str,
    ai_verdict: str,
    ai_confidence: float,
    severity: str,
    verdict_id: str | None = None,
    brand_id: str | None = None,
) -> ReviewItemRow | None:
    """Create a pending review item for a verdict that needs a human.

    Returns the row, or ``None`` if the verdict is below the review threshold
    (e.g. benign/low — auto-closed, no human time spent).
    """
    if severity not in _AUTO_REVIEW_SEVERITIES and ai_verdict != "phish":
        return None

    acct = s.get(AccountRow, account_id)
    sla_hours = acct.review_sla_hours if acct else 48
    item = ReviewItemRow(
        id=make_id("rev"),
        account_id=account_id,
        alert_id=alert_id,
        verdict_id=verdict_id,
        brand_id=brand_id,
        suspect_url=suspect_url,
        ai_verdict=ai_verdict,
        ai_confidence=ai_confidence,
        severity=severity,
        state="pending",
        sla_due_at=_utcnow() + timedelta(hours=sla_hours),
    )
    s.add(item)
    s.flush()

    notifications.notify(
        s, account_id=account_id, kind="detection",
        title=f"Review needed: {severity} detection",
        body=f"AI flagged {suspect_url} as {ai_verdict} "
             f"({int(ai_confidence * 100)}% confidence). Awaiting human review.",
        severity="critical" if severity == "critical" else "warning",
        link=f"/review/{item.id}",
    )
    log.info("review.enqueued", review_id=item.id, severity=severity, verdict=ai_verdict)
    return item


# ─────────────────────────────── Decisions ──────────────────────────────

def decide(
    s: Session,
    *,
    review_id: str,
    decision: str,
    decided_by: str,
    actor_email: str,
    human_verdict: str | None = None,
    reason: str | None = None,
    request_ip: str | None = None,
) -> dict[str, Any]:
    """Apply a reviewer decision. Returns the resulting state + takedown gate."""
    if decision not in _DECISIONS:
        raise ValueError(f"invalid decision: {decision}")
    item = s.get(ReviewItemRow, review_id)
    if item is None:
        raise ValueError("review item not found")
    if item.state != "pending":
        raise ValueError(f"review already {item.state}")

    before = {"state": item.state}
    if decision == "approve":
        item.state = "approved"
        item.human_verdict = human_verdict or item.ai_verdict
    elif decision == "reject":
        item.state = "rejected"
        item.human_verdict = human_verdict or "benign"
    else:  # escalate
        item.state = "escalated"

    item.decided_by = decided_by
    item.decision_reason = reason
    item.decided_at = _utcnow()
    s.flush()

    # Audit (hash-chained)
    audit.record(
        s, actor=actor_email, action=f"review.{decision}",
        account_id=item.account_id, target_kind="review_item", target_id=item.id,
        before=before, after={"state": item.state, "human_verdict": item.human_verdict},
        request_ip=request_ip, detail=reason,
    )

    # Active-learning feedback (label the signals)
    _feed_active_learning(s, item, decision)

    # Notify
    if decision == "escalate":
        notifications.notify(
            s, account_id=item.account_id, kind="review_assigned",
            title="Detection escalated",
            body=f"{actor_email} escalated review of {item.suspect_url}.",
            severity="warning", link=f"/review/{item.id}",
        )

    takedown_eligible = (item.state == "approved" and (item.human_verdict == "phish"))
    return {
        "review_id": item.id, "state": item.state,
        "human_verdict": item.human_verdict,
        "takedown_eligible": takedown_eligible,
    }


def _feed_active_learning(s: Session, item: ReviewItemRow, decision: str) -> None:
    """Translate a human decision into a labelled outcome for tuning."""
    try:
        from ..storage import models as orm
        outcome = {
            "approve": "true_positive",
            "reject": "false_positive",
            "escalate": "indeterminate",
        }[decision]
        # snapshot verdict signals if we can find them
        attack_family = kit = None
        cloaking = False
        composite = None
        if item.verdict_id:
            v = s.get(orm.VerdictRow, item.verdict_id)
            if v:
                attack_family, kit = v.attack_family, v.kit_match
                cloaking = bool(v.cloaking_detected)
        s.add(orm.FeedbackEventRow(
            id=make_id("fb"), alert_id=item.alert_id, tenant_id=item.account_id,
            brand_id=item.brand_id, outcome=outcome, actor=item.decided_by or "reviewer",
            attack_family=attack_family, kit_match=kit,
            cloaking_detected=cloaking, composite_score=composite,
        ))
        s.flush()
    except Exception as exc:
        log.warning("review.active_learning_feed_failed", error=str(exc))


# ─────────────────────────────── Queries ────────────────────────────────

def list_queue(
    s: Session, *, account_id: str, state: str = "pending",
    assigned_to: str | None = None, limit: int = 100,
) -> list[dict]:
    q = (
        select(ReviewItemRow)
        .where(ReviewItemRow.account_id == account_id)
        .where(ReviewItemRow.state == state)
        .order_by(ReviewItemRow.sla_due_at.asc().nullslast())
        .limit(limit)
    )
    if assigned_to:
        q = q.where(ReviewItemRow.assigned_to == assigned_to)
    return [_item_dict(r) for r in s.scalars(q).all()]


def assign(s: Session, *, review_id: str, assignee_user_id: str, actor_email: str) -> None:
    item = s.get(ReviewItemRow, review_id)
    if item is None:
        raise ValueError("review item not found")
    item.assigned_to = assignee_user_id
    s.flush()
    audit.record(s, actor=actor_email, action="review.assign",
                 account_id=item.account_id, target_kind="review_item",
                 target_id=item.id, after={"assigned_to": assignee_user_id})
    notifications.notify(
        s, account_id=item.account_id, kind="review_assigned",
        title="Review assigned to you", body=f"{item.suspect_url} needs your review.",
        severity="info", user_id=assignee_user_id, link=f"/review/{item.id}",
    )


def sweep_sla_breaches(s: Session) -> int:
    """Find pending items past SLA and raise a breach notification. Returns count."""
    now = _utcnow()
    rows = s.scalars(
        select(ReviewItemRow).where(ReviewItemRow.state == "pending")
    ).all()
    breached = 0
    for r in rows:
        due = _aware(r.sla_due_at)
        if due and due < now:
            breached += 1
            notifications.notify(
                s, account_id=r.account_id, kind="sla_breach",
                title="Review SLA breached",
                body=f"{r.suspect_url} has been pending review past its SLA.",
                severity="critical", link=f"/review/{r.id}", send_email=True,
            )
    return breached


def queue_stats(s: Session, *, account_id: str) -> dict[str, int]:
    rows = s.execute(
        select(ReviewItemRow.state, func.count())
        .where(ReviewItemRow.account_id == account_id)
        .group_by(ReviewItemRow.state)
    ).all()
    return {state: count for state, count in rows}


def _item_dict(r: ReviewItemRow) -> dict:
    due = _aware(r.sla_due_at)
    created = _aware(r.created_at)
    return {
        "id": r.id, "account_id": r.account_id, "alert_id": r.alert_id,
        "brand_id": r.brand_id, "suspect_url": r.suspect_url,
        "ai_verdict": r.ai_verdict, "ai_confidence": r.ai_confidence,
        "severity": r.severity, "state": r.state, "assigned_to": r.assigned_to,
        "human_verdict": r.human_verdict, "decided_by": r.decided_by,
        "sla_due_at": due.isoformat() if due else None,
        "created_at": created.isoformat() if created else None,
        "overdue": bool(due and due < _utcnow() and r.state == "pending"),
    }


__all__ = [
    "enqueue_for_review", "decide", "list_queue", "assign",
    "sweep_sla_breaches", "queue_stats",
]
