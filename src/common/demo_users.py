"""Canonical demo-user matrix — the full role × tier set.

Single source of truth shared by the seed script and the login page so the
two never drift. Every combination a judge/evaluator might want to try:

* One Owner per tier (Personal / Pro / Business / Enterprise)
* On the Business + Enterprise accounts, a full role set
  (Owner, Admin, Analyst, Reviewer, Viewer)
* One platform-staff super-admin
* One MFA-enabled account to demo the second factor

All accounts share one password for convenience (clearly a demo affordance,
never a production pattern).
"""
from __future__ import annotations

DEMO_PASSWORD = "DemoPass123!"

# Each entry: email, role, tier, account_name, mfa (bool), platform_staff (bool)
DEMO_USERS: list[dict] = [
    # ── Owners, one per tier ──────────────────────────────────────────
    {"email": "owner@personal.demo", "role": "owner", "tier": "personal",
     "account": "Personal Demo", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},
    {"email": "owner@pro.demo", "role": "owner", "tier": "pro",
     "account": "Pro Demo", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},
    {"email": "owner@business.demo", "role": "owner", "tier": "business",
     "account": "Business Demo Inc", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},
    {"email": "owner@enterprise.demo", "role": "owner", "tier": "enterprise",
     "account": "Enterprise Demo Corp", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},

    # ── Full role set on the Business account ─────────────────────────
    {"email": "admin@business.demo", "role": "admin", "tier": "business",
     "account": "Business Demo Inc", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},
    {"email": "analyst@business.demo", "role": "analyst", "tier": "business",
     "account": "Business Demo Inc", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},
    {"email": "reviewer@business.demo", "role": "reviewer", "tier": "business",
     "account": "Business Demo Inc", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},
    {"email": "viewer@business.demo", "role": "viewer", "tier": "business",
     "account": "Business Demo Inc", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},

    # ── Full role set on the Enterprise account ───────────────────────
    {"email": "admin@enterprise.demo", "role": "admin", "tier": "enterprise",
     "account": "Enterprise Demo Corp", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},
    {"email": "analyst@enterprise.demo", "role": "analyst", "tier": "enterprise",
     "account": "Enterprise Demo Corp", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},
    {"email": "reviewer@enterprise.demo", "role": "reviewer", "tier": "enterprise",
     "account": "Enterprise Demo Corp", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},
    {"email": "viewer@enterprise.demo", "role": "viewer", "tier": "enterprise",
     "account": "Enterprise Demo Corp", "mfa": False, "staff": False,
     "password": DEMO_PASSWORD},

    # ── MFA-enabled account (demos the second factor) ─────────────────
    {"email": "mfa.reviewer@enterprise.demo", "role": "reviewer", "tier": "enterprise",
     "account": "Enterprise Demo Corp", "mfa": True, "staff": False,
     "password": DEMO_PASSWORD},

    # ── Platform super-admin (internal staff) ─────────────────────────
    {"email": "staff@doppeldomain.demo", "role": "owner", "tier": "enterprise",
     "account": "DoppelDomain Platform", "mfa": False, "staff": True,
     "password": DEMO_PASSWORD},
]


__all__ = ["DEMO_USERS", "DEMO_PASSWORD"]
