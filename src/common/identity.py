"""Identity service — signup, authentication, MFA, sessions, memberships.

Pure business logic over the identity tables. Routes call these functions;
they never touch the ORM directly. Every function that changes state returns
plain dicts/dataclasses, not ORM rows, so callers can't accidentally mutate
detached objects.

Account-lockout policy: 5 failed logins locks the user for 15 minutes. This
is a baseline brute-force defence; tiers that enforce MFA add a second factor.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common import security
from ..common.ids import make_id
from ..common.logging import get_logger
from ..common.rbac import Role, Tier, limits_for, permissions_for
from ..storage.identity_models import (
    AccountRow,
    MembershipRow,
    OidcIdentityRow,
    UserRow,
    WebSessionRow,
)

log = get_logger(__name__)

_MAX_FAILED = 5
_LOCKOUT = timedelta(minutes=15)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    """Coerce a possibly-naive DB datetime to UTC-aware for safe comparison.

    SQLite (and some drivers) drop tzinfo on round-trip, so a value we stored
    as aware comes back naive. Comparing naive vs aware raises TypeError, which
    would silently break lockout/expiry checks. We treat naive values as UTC.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ───────────────────────────── Errors ───────────────────────────────────

class AuthError(Exception):
    """Raised on any authentication failure (caller maps to 401/403)."""


class MfaRequired(Exception):
    """Raised when credentials are valid but a TOTP code is still needed.

    Carries a short-lived ``challenge`` the client echoes back with the code.
    """

    def __init__(self, user_id: str) -> None:
        super().__init__("mfa_required")
        self.user_id = user_id


# ─────────────────────────── Result types ───────────────────────────────

@dataclass
class AuthedUser:
    user_id: str
    email: str
    full_name: str
    account_id: str
    role: Role
    tier: Tier
    is_platform_staff: bool

    @property
    def permissions(self) -> set[str]:
        return {p.value for p in permissions_for(self.role)}


# ─────────────────────────── Account / user ─────────────────────────────

def create_account(
    s: Session,
    *,
    name: str,
    tier: Tier = Tier.PERSONAL,
    account_type: str = "personal",
) -> AccountRow:
    limits = limits_for(tier)
    acct = AccountRow(
        id=make_id("acct"),
        name=name,
        tier=tier.value,
        account_type=account_type,
        daily_inspect_cap=limits.daily_inspect_cap,
        review_sla_hours=limits.review_sla_hours,
        mfa_required=False,
    )
    s.add(acct)
    s.flush()
    log.info("account.created", account_id=acct.id, tier=tier.value)
    return acct


def create_user(
    s: Session,
    *,
    email: str,
    full_name: str = "",
    password: str | None = None,
    is_platform_staff: bool = False,
) -> UserRow:
    email = email.strip().lower()
    existing = s.scalar(select(UserRow).where(UserRow.email == email))
    if existing is not None:
        raise AuthError("email already registered")
    user = UserRow(
        id=make_id("user"),
        email=email,
        full_name=full_name,
        password_hash=security.hash_password(password) if password else None,
        is_platform_staff=is_platform_staff,
    )
    s.add(user)
    s.flush()
    log.info("user.created", user_id=user.id, email=email)
    return user


def add_membership(
    s: Session, *, user_id: str, account_id: str, role: Role, invited_by: str | None = None
) -> MembershipRow:
    m = MembershipRow(
        id=make_id("mem"),
        user_id=user_id,
        account_id=account_id,
        role=role.value,
        invited_by=invited_by,
    )
    s.add(m)
    s.flush()
    return m


def signup(
    s: Session, *, email: str, password: str, full_name: str = "",
    account_name: str | None = None, tier: Tier = Tier.PERSONAL,
) -> AuthedUser:
    """Self-serve signup: creates an account + owner user in one step.

    Works for individuals (Personal) right up to Enterprise trials.
    """
    acct = create_account(
        s, name=account_name or (full_name or email.split("@")[0]),
        tier=tier,
        account_type="personal" if tier in (Tier.PERSONAL, Tier.PRO) else "business",
    )
    user = create_user(s, email=email, full_name=full_name, password=password)
    add_membership(s, user_id=user.id, account_id=acct.id, role=Role.OWNER)
    return AuthedUser(
        user_id=user.id, email=user.email, full_name=user.full_name,
        account_id=acct.id, role=Role.OWNER, tier=tier,
        is_platform_staff=user.is_platform_staff,
    )


# ───────────────────────────── Login flow ───────────────────────────────

def _resolve_membership(s: Session, user_id: str, account_id: str | None) -> MembershipRow:
    q = select(MembershipRow).where(
        MembershipRow.user_id == user_id, MembershipRow.is_active.is_(True)
    )
    if account_id:
        q = q.where(MembershipRow.account_id == account_id)
    m = s.scalar(q)
    if m is None:
        raise AuthError("no active account membership")
    return m


def authenticate_password(
    s: Session, *, email: str, password: str, account_id: str | None = None
) -> AuthedUser:
    """Verify email+password. Raises ``MfaRequired`` if the user has MFA on."""
    email = email.strip().lower()
    user = s.scalar(select(UserRow).where(UserRow.email == email))
    if user is None or not user.is_active:
        raise AuthError("invalid credentials")
    if _aware(user.locked_until) and _aware(user.locked_until) > _utcnow():
        raise AuthError("account temporarily locked")
    if not user.password_hash or not security.verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= _MAX_FAILED:
            user.locked_until = _utcnow() + _LOCKOUT
            log.warning("auth.locked", user_id=user.id)
        s.flush()
        raise AuthError("invalid credentials")

    user.failed_login_count = 0
    user.locked_until = None
    s.flush()

    if user.mfa_enabled:
        raise MfaRequired(user.id)

    return _finish_login(s, user, account_id)


def complete_mfa(
    s: Session, *, user_id: str, code: str, account_id: str | None = None
) -> AuthedUser:
    user = s.get(UserRow, user_id)
    if user is None or not user.is_active:
        raise AuthError("invalid user")
    ok = security.verify_totp(user.mfa_secret or "", code)
    if not ok:
        # try recovery codes
        if security.verify_recovery_code(code, user.mfa_recovery_hashes or []):
            remaining = [
                h for h in (user.mfa_recovery_hashes or [])
                if h != security.hash_recovery_code(code.strip())
            ]
            user.mfa_recovery_hashes = remaining
            s.flush()
            log.info("auth.recovery_code_used", user_id=user.id)
        else:
            raise AuthError("invalid MFA code")
    return _finish_login(s, user, account_id)


def _finish_login(s: Session, user: UserRow, account_id: str | None) -> AuthedUser:
    m = _resolve_membership(s, user.id, account_id)
    acct = s.get(AccountRow, m.account_id)
    if acct is None or not acct.is_active:
        raise AuthError("account inactive")
    user.last_login_at = _utcnow()
    s.flush()
    return AuthedUser(
        user_id=user.id, email=user.email, full_name=user.full_name,
        account_id=acct.id, role=Role(m.role), tier=Tier(acct.tier),
        is_platform_staff=user.is_platform_staff,
    )


# ─────────────────────────────── MFA setup ──────────────────────────────

def begin_mfa_enrolment(s: Session, *, user_id: str) -> dict:
    """Generate a secret + provisioning URI. Not enabled until confirmed."""
    user = s.get(UserRow, user_id)
    if user is None:
        raise AuthError("invalid user")
    secret = security.new_mfa_secret()
    user.mfa_secret = secret  # stored but mfa_enabled stays False until confirm
    s.flush()
    uri = security.mfa_provisioning_uri(secret, account_name=user.email)
    return {"secret": secret, "provisioning_uri": uri}


def confirm_mfa(s: Session, *, user_id: str, code: str) -> list[str]:
    """Confirm enrolment with a valid code; returns one-time recovery codes."""
    user = s.get(UserRow, user_id)
    if user is None or not user.mfa_secret:
        raise AuthError("no pending MFA enrolment")
    if not security.verify_totp(user.mfa_secret, code):
        raise AuthError("invalid MFA code")
    codes = security.new_recovery_codes()
    user.mfa_recovery_hashes = [security.hash_recovery_code(c) for c in codes]
    user.mfa_enabled = True
    s.flush()
    log.info("auth.mfa_enabled", user_id=user.id)
    return codes


# ─────────────────────────── Web sessions ───────────────────────────────

def create_web_session(
    s: Session, au: AuthedUser, *, ip: str | None, user_agent: str | None,
    mfa_satisfied: bool = True,
) -> str:
    sid = make_id("sess")
    s.add(WebSessionRow(
        id=sid, user_id=au.user_id, account_id=au.account_id, role=au.role.value,
        ip=ip, user_agent=user_agent, mfa_satisfied=mfa_satisfied,
    ))
    s.flush()
    return sid


def load_web_session(s: Session, sid: str) -> AuthedUser | None:
    row = s.get(WebSessionRow, sid)
    if row is None or row.revoked_at is not None:
        return None
    user = s.get(UserRow, row.user_id)
    acct = s.get(AccountRow, row.account_id)
    if user is None or acct is None or not user.is_active or not acct.is_active:
        return None
    row.last_seen_at = _utcnow()
    s.flush()
    return AuthedUser(
        user_id=user.id, email=user.email, full_name=user.full_name,
        account_id=acct.id, role=Role(row.role), tier=Tier(acct.tier),
        is_platform_staff=user.is_platform_staff,
    )


def revoke_web_session(s: Session, sid: str) -> None:
    row = s.get(WebSessionRow, sid)
    if row is not None and row.revoked_at is None:
        row.revoked_at = _utcnow()
        s.flush()


# ─────────────────────────────── OIDC / SSO ─────────────────────────────

def upsert_oidc_user(
    s: Session, *, issuer: str, subject: str, email: str, full_name: str = "",
    default_tier: Tier = Tier.BUSINESS,
) -> AuthedUser:
    """Find or create a user from a verified OIDC claim set (JIT provisioning)."""
    email = email.strip().lower()
    link = s.scalar(
        select(OidcIdentityRow).where(
            OidcIdentityRow.issuer == issuer, OidcIdentityRow.subject == subject
        )
    )
    if link is not None:
        user = s.get(UserRow, link.user_id)
        if user is None:
            raise AuthError("orphaned OIDC link")
    else:
        user = s.scalar(select(UserRow).where(UserRow.email == email))
        if user is None:
            # JIT-provision a new account + owner for first SSO login
            au = signup(
                s, email=email, password=security.new_api_secret(),  # random; SSO-only
                full_name=full_name, tier=default_tier,
            )
            user = s.get(UserRow, au.user_id)
            user.password_hash = None  # SSO-only
        s.add(OidcIdentityRow(
            id=make_id("oidc"), user_id=user.id, issuer=issuer,
            subject=subject, email=email,
        ))
        s.flush()
    m = _resolve_membership(s, user.id, None)
    acct = s.get(AccountRow, m.account_id)
    user.last_login_at = _utcnow()
    s.flush()
    return AuthedUser(
        user_id=user.id, email=user.email, full_name=user.full_name,
        account_id=acct.id, role=Role(m.role), tier=Tier(acct.tier),
        is_platform_staff=user.is_platform_staff,
    )


__all__ = [
    "AuthError", "MfaRequired", "AuthedUser",
    "create_account", "create_user", "add_membership", "signup",
    "authenticate_password", "complete_mfa",
    "begin_mfa_enrolment", "confirm_mfa",
    "create_web_session", "load_web_session", "revoke_web_session",
    "upsert_oidc_user",
]
