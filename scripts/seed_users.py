"""Seed the demo identity matrix — every role across every tier.

Idempotent: re-running reuses existing accounts/users. Creates accounts keyed
by name, then attaches users with their role. For the MFA-flagged account it
enables TOTP and prints a ready-to-use current code so a live demo can show
the second factor without a phone.

Usage::

    python -m scripts.seed_users
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyotp  # noqa: E402
from sqlalchemy import select  # noqa: E402

from src.common import identity as idsvc  # noqa: E402
from src.common import security  # noqa: E402
from src.common.demo_users import DEMO_PASSWORD, DEMO_USERS  # noqa: E402
from src.common.logging import get_logger  # noqa: E402
from src.common.rbac import Role, Tier  # noqa: E402
from src.storage.db import session_scope  # noqa: E402
from src.storage.identity_models import AccountRow, MembershipRow, UserRow  # noqa: E402
from src.storage.init_db import init_db  # noqa: E402

log = get_logger(__name__)


def _get_or_create_account(s, name: str, tier: Tier) -> AccountRow:
    acct = s.scalar(select(AccountRow).where(AccountRow.name == name))
    if acct is None:
        acct = idsvc.create_account(s, name=name, tier=tier,
                                    account_type="personal" if tier in (Tier.PERSONAL, Tier.PRO) else "business")
        if tier == Tier.ENTERPRISE:
            acct.mfa_required = False  # leave optional so non-MFA demo users still log in
    return acct


def _get_or_create_user(s, email: str, full_name: str, password: str, staff: bool) -> UserRow:
    u = s.scalar(select(UserRow).where(UserRow.email == email.lower()))
    if u is None:
        u = idsvc.create_user(s, email=email, full_name=full_name, password=password,
                              is_platform_staff=staff)
    return u


def seed() -> None:
    init_db()
    mfa_lines: list[str] = []

    with session_scope() as s:
        for entry in DEMO_USERS:
            tier = Tier(entry["tier"])
            role = Role(entry["role"])
            acct = _get_or_create_account(s, entry["account"], tier)
            full_name = f"{entry['role'].title()} ({entry['tier']})"
            user = _get_or_create_user(s, entry["email"], full_name,
                                       entry["password"], entry["staff"])

            # membership (skip if already present)
            existing = s.scalar(
                select(MembershipRow).where(
                    MembershipRow.user_id == user.id,
                    MembershipRow.account_id == acct.id,
                )
            )
            if existing is None:
                idsvc.add_membership(s, user_id=user.id, account_id=acct.id, role=role)

            # MFA enablement for flagged demo accounts
            if entry.get("mfa") and not user.mfa_enabled:
                secret = security.new_mfa_secret()
                user.mfa_secret = secret
                user.mfa_enabled = True
                user.mfa_recovery_hashes = [
                    security.hash_recovery_code(c) for c in security.new_recovery_codes()
                ]
                s.flush()
            if entry.get("mfa") and user.mfa_secret:
                code = pyotp.TOTP(user.mfa_secret).now()
                mfa_lines.append(f"  {entry['email']}  current TOTP: {code}  (secret {user.mfa_secret})")

    print("\n" + "=" * 64)
    print(f"  Seeded {len(DEMO_USERS)} demo users across the role × tier matrix")
    print(f"  Shared password: {DEMO_PASSWORD}")
    print("=" * 64)
    by_tier: dict[str, list[str]] = {}
    for e in DEMO_USERS:
        by_tier.setdefault(e["tier"], []).append(f"{e['role']}: {e['email']}")
    for tier, rows in by_tier.items():
        print(f"\n  [{tier.upper()}]")
        for r in rows:
            print(f"    {r}")
    if mfa_lines:
        print("\n  MFA-enabled demo accounts (use the code shown):")
        for line in mfa_lines:
            print(line)
    print("\n  Login at:  /login")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    seed()
