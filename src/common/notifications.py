"""Notifications & email alerts.

Two channels off one event:

* **In-app** — a row in ``notifications`` shown in the UI feed.
* **Email** — sent via SMTP when ``email_enabled`` and the recipient's prefs
  allow it; otherwise the email is *logged* (so the flow is testable and the
  demo works without a mail server).

Event kinds (REQ-NOTIF-01..04): ``detection`` (new high-severity find),
``review_assigned``, ``sla_breach``, ``system_error``, ``report_ready``.

Severity ordering lets a user say "email me only warning and above".
"""
from __future__ import annotations

import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.ids import make_id
from ..common.logging import get_logger
from ..common.settings import get_settings
from ..storage.identity_models import (
    NotificationPrefRow,
    NotificationRow,
    UserRow,
    MembershipRow,
)

log = get_logger(__name__)

_SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sev_ge(a: str, b: str) -> bool:
    return _SEVERITY_ORDER.get(a, 0) >= _SEVERITY_ORDER.get(b, 0)


# ───────────────────────────── In-app feed ──────────────────────────────

def notify(
    s: Session,
    *,
    account_id: str,
    kind: str,
    title: str,
    body: str = "",
    severity: str = "info",
    user_id: str | None = None,
    link: str | None = None,
    send_email: bool = True,
) -> str:
    """Create an in-app notification and (optionally) fan out emails."""
    n = NotificationRow(
        id=make_id("ntf"), account_id=account_id, user_id=user_id,
        kind=kind, severity=severity, title=title, body=body, link=link,
    )
    s.add(n)
    s.flush()

    if send_email:
        _maybe_email(s, account_id=account_id, kind=kind, severity=severity,
                     title=title, body=body, link=link, user_id=user_id,
                     notification_id=n.id)
    return n.id


def list_for_user(s: Session, *, user_id: str, account_id: str,
                  unread_only: bool = False, limit: int = 50) -> list[dict]:
    q = (
        select(NotificationRow)
        .where(NotificationRow.account_id == account_id)
        .where((NotificationRow.user_id == user_id) | (NotificationRow.user_id.is_(None)))
        .order_by(NotificationRow.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        q = q.where(NotificationRow.read_at.is_(None))
    rows = s.scalars(q).all()
    return [
        {
            "id": r.id, "kind": r.kind, "severity": r.severity, "title": r.title,
            "body": r.body, "link": r.link,
            "read": r.read_at is not None,
            "created_at": (r.created_at.replace(tzinfo=timezone.utc)
                           if r.created_at and r.created_at.tzinfo is None
                           else r.created_at).isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def mark_read(s: Session, *, notification_id: str) -> None:
    n = s.get(NotificationRow, notification_id)
    if n and n.read_at is None:
        n.read_at = _utcnow()
        s.flush()


# ───────────────────────────── Preferences ──────────────────────────────

def get_pref(s: Session, *, user_id: str, account_id: str, kind: str) -> NotificationPrefRow | None:
    return s.scalar(
        select(NotificationPrefRow).where(
            NotificationPrefRow.user_id == user_id,
            NotificationPrefRow.account_id == account_id,
            NotificationPrefRow.kind == kind,
        )
    )


def set_pref(s: Session, *, user_id: str, account_id: str, kind: str,
             in_app: bool = True, email: bool = True, min_severity: str = "info") -> None:
    pref = get_pref(s, user_id=user_id, account_id=account_id, kind=kind)
    if pref is None:
        pref = NotificationPrefRow(
            id=make_id("npref"), user_id=user_id, account_id=account_id, kind=kind,
        )
        s.add(pref)
    pref.in_app, pref.email, pref.min_severity = in_app, email, min_severity
    s.flush()


# ───────────────────────────── Email channel ────────────────────────────

def _recipients(s: Session, *, account_id: str, kind: str, severity: str,
                user_id: str | None) -> list[str]:
    """Resolve which users should be emailed for this event."""
    if user_id:
        u = s.get(UserRow, user_id)
        users = [u] if u else []
    else:
        member_ids = [m.user_id for m in s.scalars(
            select(MembershipRow).where(
                MembershipRow.account_id == account_id,
                MembershipRow.is_active.is_(True),
            )
        ).all()]
        users = [s.get(UserRow, mid) for mid in member_ids]
        users = [u for u in users if u]

    out: list[str] = []
    for u in users:
        if not u or not u.is_active:
            continue
        pref = get_pref(s, user_id=u.id, account_id=account_id, kind=kind)
        if pref is None:
            # default: email on warning+ for everyone
            if _sev_ge(severity, "warning"):
                out.append(u.email)
        elif pref.email and _sev_ge(severity, pref.min_severity):
            out.append(u.email)
    return out


def _maybe_email(s: Session, *, account_id: str, kind: str, severity: str,
                 title: str, body: str, link: str | None, user_id: str | None,
                 notification_id: str) -> None:
    settings = get_settings()
    recipients = _recipients(s, account_id=account_id, kind=kind,
                             severity=severity, user_id=user_id)
    if not recipients:
        return

    full_link = (settings.app_base_url + link) if link else settings.app_base_url
    html = _render_email(title=title, body=body, severity=severity, link=full_link)

    if not settings.email_enabled or not settings.smtp_host:
        log.info("email.skipped_not_configured", kind=kind, severity=severity,
                 recipients=len(recipients), title=title)
    else:
        try:
            _send_smtp(settings, recipients, subject=f"[DoppelDomain] {title}", html=html)
            log.info("email.sent", kind=kind, recipients=len(recipients))
        except Exception as exc:
            log.warning("email.send_failed", error=str(exc))

    n = s.get(NotificationRow, notification_id)
    if n:
        n.emailed_at = _utcnow()
        s.flush()


def _render_email(*, title: str, body: str, severity: str, link: str) -> str:
    colour = {"info": "#3b82f6", "warning": "#f59e0b", "critical": "#ef4444"}.get(severity, "#3b82f6")
    return f"""\
<div style="font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:560px;margin:0 auto">
  <div style="border-left:4px solid {colour};padding:16px 20px;background:#0b0f16;color:#e8edf4;border-radius:8px">
    <div style="font-size:12px;letter-spacing:.05em;color:{colour};text-transform:uppercase">{severity}</div>
    <h2 style="margin:6px 0 10px;font-size:18px;color:#fff">{title}</h2>
    <p style="margin:0 0 16px;color:#cbd5e1;line-height:1.5">{body}</p>
    <a href="{link}" style="display:inline-block;background:{colour};color:#fff;
       text-decoration:none;padding:9px 16px;border-radius:6px;font-weight:600">View in DoppelDomain</a>
  </div>
  <p style="font-size:11px;color:#64748b;text-align:center;margin-top:12px">
    You received this because of your DoppelDomain notification preferences.</p>
</div>"""


def _send_smtp(settings, recipients: list[str], *, subject: str, html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.email_from, recipients, msg.as_string())


__all__ = [
    "notify", "list_for_user", "mark_read", "get_pref", "set_pref",
]
