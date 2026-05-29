"""Identity, access, and human-in-the-loop ORM models (v0.3).

These extend the existing schema in ``models.py`` without modifying it. New
tables:

* ``accounts``        — tier-aware organisational unit (supersedes bare tenant)
* ``users``           — human identities (email + password + optional MFA)
* ``memberships``     — user ↔ account with a role (a user can belong to many)
* ``web_sessions``    — server-side session records (revocable)
* ``oidc_identities`` — links an external SSO subject to a user
* ``review_items``    — the human-in-the-loop queue (AI proposes, human decides)
* ``notifications``   — in-app notification feed
* ``notification_prefs`` — per-user channel/event subscription
* ``reports``         — generated report artefacts (PDF/CSV) metadata

Every table carries ``account_id`` for tenant isolation. ``accounts.id`` is the
canonical tenant id; the legacy ``tenants`` table is kept for backward compat
and mirrored on account creation.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────── Accounts ───────────────────────────────

class AccountRow(Base):
    """A customer account. ``tier`` gates features; one account = one tenant.

    Works for any customer shape: a single person (Personal), a creator (Pro),
    an SMB (Business), or a large org (Enterprise).
    """

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tier: Mapped[str] = mapped_column(String(40), default="personal", index=True)
    # account_type ∈ {personal, business} — informational, drives onboarding UX
    account_type: Mapped[str] = mapped_column(String(20), default="personal")
    # Org-wide security policy
    mfa_required: Mapped[bool] = mapped_column(Boolean, default=False)
    sso_only: Mapped[bool] = mapped_column(Boolean, default=False)  # disable password login
    # Quotas (snapshot from tier at creation; can be overridden per account)
    daily_inspect_cap: Mapped[int | None] = mapped_column(Integer)
    review_sla_hours: Mapped[int] = mapped_column(Integer, default=48)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ──────────────────────────────── Users ─────────────────────────────────

class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str | None] = mapped_column(String(200))  # None = SSO-only user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_platform_staff: Mapped[bool] = mapped_column(Boolean, default=False)

    # MFA
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64))
    mfa_recovery_hashes: Mapped[list] = mapped_column(JSON, default=list)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MembershipRow(Base):
    """A user's role within an account. Composite-unique on (user, account)."""

    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40), ForeignKey("users.id"), index=True)
    account_id: Mapped[str] = mapped_column(String(40), ForeignKey("accounts.id"), index=True)
    role: Mapped[str] = mapped_column(String(40), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    invited_by: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ─────────────────────────────── Sessions ───────────────────────────────

class WebSessionRow(Base):
    """Server-side session record so we can revoke a browser session."""

    __tablename__ = "web_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # opaque session id
    user_id: Mapped[str] = mapped_column(String(40), ForeignKey("users.id"), index=True)
    account_id: Mapped[str] = mapped_column(String(40), index=True)
    role: Mapped[str] = mapped_column(String(40))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    mfa_satisfied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OidcIdentityRow(Base):
    """Links an external IdP subject to a local user (SSO)."""

    __tablename__ = "oidc_identities"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40), ForeignKey("users.id"), index=True)
    issuer: Mapped[str] = mapped_column(String(320), index=True)
    subject: Mapped[str] = mapped_column(String(320), index=True)
    email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ──────────────────── Human-in-the-loop review queue ────────────────────

class ReviewItemRow(Base):
    """An AI verdict awaiting a human decision.

    The pipeline never auto-actions a high-severity verdict: it creates a
    review item in state ``pending``. A Reviewer approves/rejects/escalates;
    only an approved 'phish' verdict may proceed to takedown submission.
    """

    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(40), index=True)
    alert_id: Mapped[str] = mapped_column(String(40), index=True)
    verdict_id: Mapped[str | None] = mapped_column(String(40))
    brand_id: Mapped[str | None] = mapped_column(String(40), index=True)
    suspect_url: Mapped[str] = mapped_column(String(2000))

    ai_verdict: Mapped[str] = mapped_column(String(40))         # phish/suspicious/benign
    ai_confidence: Mapped[float] = mapped_column(default=0.0)
    severity: Mapped[str] = mapped_column(String(20), default="medium")

    # state ∈ {pending, approved, rejected, escalated}
    state: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(40), index=True)
    decided_by: Mapped[str | None] = mapped_column(String(40))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    human_verdict: Mapped[str | None] = mapped_column(String(40))  # may differ from AI

    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ───────────────────────────── Notifications ────────────────────────────

class NotificationRow(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(40), index=True)
    user_id: Mapped[str | None] = mapped_column(String(40), index=True)  # None = account-wide
    kind: Mapped[str] = mapped_column(String(60), index=True)  # detection, review_assigned, sla_breach, system_error, report_ready
    severity: Mapped[str] = mapped_column(String(20), default="info")    # info, warning, critical
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str | None] = mapped_column(String(500))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class NotificationPrefRow(Base):
    """Per-user subscription: which event kinds, which channels."""

    __tablename__ = "notification_prefs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40), ForeignKey("users.id"), index=True)
    account_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(60))
    in_app: Mapped[bool] = mapped_column(Boolean, default=True)
    email: Mapped[bool] = mapped_column(Boolean, default=True)
    min_severity: Mapped[str] = mapped_column(String(20), default="info")


# ─────────────────────────────── Reports ────────────────────────────────

class ReportRow(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(60))   # detection_summary, board_pack, audit_export, brand
    fmt: Mapped[str] = mapped_column(String(10))     # pdf, csv, json
    title: Mapped[str] = mapped_column(String(300))
    path: Mapped[str] = mapped_column(String(600))
    params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    generated_by: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


__all__ = [
    "AccountRow", "UserRow", "MembershipRow", "WebSessionRow", "OidcIdentityRow",
    "ReviewItemRow", "NotificationRow", "NotificationPrefRow", "ReportRow",
]
