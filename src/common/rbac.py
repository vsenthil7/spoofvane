"""Role-based access control and account tiers.

This module is the single source of truth for *who can do what*. It defines:

* **Roles** — what a user is allowed to do inside an account (Owner → Viewer,
  plus a non-human Service role for API keys).
* **Tiers** — the commercial plan an account is on (Personal → Enterprise),
  which gates *features* and *quotas* rather than permissions.
* **Permissions** — fine-grained verbs (``alerts:read``, ``takedown:approve``…)
  that routes require. Roles map to sets of permissions.

The split matters: a *role* answers "is this person allowed?", a *tier*
answers "does this account pay for the feature?". A request must satisfy
both — an Owner on the Personal tier still cannot use SSO, and an Analyst
on the Enterprise tier still cannot delete the account.

Design goals
------------
* Pure data + pure functions — no DB, no FastAPI imports — so it is trivially
  testable and importable from anywhere (workers, scripts, API).
* Adding a permission is a one-line change here; routes reference the constant.
"""
from __future__ import annotations

from enum import Enum


# ───────────────────────── Permissions ──────────────────────────────────
# Fine-grained verbs. Format: ``<resource>:<action>``. Routes declare the
# permission they need; roles below enumerate which they grant.

class Permission(str, Enum):
    # Brands
    BRANDS_READ = "brands:read"
    BRANDS_WRITE = "brands:write"
    BRANDS_DELETE = "brands:delete"

    # Detection pipeline
    DISCOVERY_RUN = "discovery:run"
    INSPECTION_READ = "inspection:read"

    # Alerts
    ALERTS_READ = "alerts:read"
    ALERTS_TRIAGE = "alerts:triage"      # add notes, change status
    ALERTS_ASSIGN = "alerts:assign"      # route to a reviewer

    # Human-in-the-loop review (AI proposes, human disposes)
    REVIEW_READ = "review:read"
    REVIEW_DECIDE = "review:decide"      # approve / reject an AI verdict
    REVIEW_ESCALATE = "review:escalate"

    # Takedown — the high-blast-radius action; always behind a human gate
    TAKEDOWN_DRAFT = "takedown:draft"
    TAKEDOWN_APPROVE = "takedown:approve"
    TAKEDOWN_SUBMIT = "takedown:submit"

    # Reports
    REPORTS_READ = "reports:read"
    REPORTS_GENERATE = "reports:generate"

    # Notifications (own preferences)
    NOTIFICATIONS_MANAGE = "notifications:manage"

    # Audit
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # Account & member administration
    MEMBERS_READ = "members:read"
    MEMBERS_INVITE = "members:invite"
    MEMBERS_MANAGE = "members:manage"    # change roles, deactivate
    ACCOUNT_MANAGE = "account:manage"    # rename, change tier, delete
    APIKEYS_MANAGE = "apikeys:manage"
    BILLING_MANAGE = "billing:manage"

    # Platform super-admin (cross-account, internal staff only)
    PLATFORM_ADMIN = "platform:admin"


# ───────────────────────────── Roles ────────────────────────────────────

class Role(str, Enum):
    OWNER = "owner"        # full control incl. billing + delete account
    ADMIN = "admin"        # everything except destroying the account / billing
    ANALYST = "analyst"    # triage + draft takedowns, cannot approve own
    REVIEWER = "reviewer"  # the human-in-the-loop: approves/rejects AI verdicts + takedowns
    VIEWER = "viewer"      # read-only
    SERVICE = "service"    # non-human (API keys / SIEM); read + ingest, never approve
    PLATFORM = "platform"  # internal staff, cross-tenant


_P = Permission

# Permission grants per role. Higher roles are supersets where sensible, but
# we enumerate explicitly rather than inherit, so the matrix is auditable at
# a glance and a reviewer's *approval* power is never silently granted to an
# analyst.
_ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.VIEWER: {
        _P.BRANDS_READ, _P.INSPECTION_READ, _P.ALERTS_READ,
        _P.REPORTS_READ, _P.NOTIFICATIONS_MANAGE,
    },
    Role.SERVICE: {
        # Machine identity: can read everything and run discovery (for
        # scheduled jobs / SIEM pulls) but can NEVER make a human-gated
        # decision (no review:decide, no takedown:approve).
        _P.BRANDS_READ, _P.INSPECTION_READ, _P.ALERTS_READ, _P.REVIEW_READ,
        _P.DISCOVERY_RUN, _P.REPORTS_READ, _P.REPORTS_GENERATE, _P.AUDIT_READ,
    },
    Role.ANALYST: {
        _P.BRANDS_READ, _P.BRANDS_WRITE, _P.DISCOVERY_RUN, _P.INSPECTION_READ,
        _P.ALERTS_READ, _P.ALERTS_TRIAGE, _P.ALERTS_ASSIGN,
        _P.REVIEW_READ, _P.REVIEW_ESCALATE,
        _P.TAKEDOWN_DRAFT,
        _P.REPORTS_READ, _P.REPORTS_GENERATE, _P.NOTIFICATIONS_MANAGE,
    },
    Role.REVIEWER: {
        # The human-in-the-loop authority. Adds the decide/approve verbs the
        # analyst lacks. This separation is deliberate: the person who drafts
        # is not necessarily the person who approves (segregation of duties).
        _P.BRANDS_READ, _P.INSPECTION_READ,
        _P.ALERTS_READ, _P.ALERTS_TRIAGE, _P.ALERTS_ASSIGN,
        _P.REVIEW_READ, _P.REVIEW_DECIDE, _P.REVIEW_ESCALATE,
        _P.TAKEDOWN_DRAFT, _P.TAKEDOWN_APPROVE,
        _P.REPORTS_READ, _P.REPORTS_GENERATE, _P.NOTIFICATIONS_MANAGE,
    },
    Role.ADMIN: set(),   # filled below = everything except owner-only verbs
    Role.OWNER: set(),   # filled below = everything in-account
    Role.PLATFORM: {p for p in Permission},  # everything, everywhere
}

# Owner-only verbs — destroying or commercially changing the account.
_OWNER_ONLY: set[Permission] = {_P.ACCOUNT_MANAGE, _P.BILLING_MANAGE}

# Admin = every in-account permission except the owner-only ones and the
# platform super-admin verb.
_ALL_IN_ACCOUNT = {p for p in Permission if p is not _P.PLATFORM_ADMIN}
_ROLE_PERMISSIONS[Role.ADMIN] = (_ALL_IN_ACCOUNT - _OWNER_ONLY) | {
    _P.TAKEDOWN_SUBMIT,
}
_ROLE_PERMISSIONS[Role.OWNER] = set(_ALL_IN_ACCOUNT)


def permissions_for(role: Role) -> set[Permission]:
    """Return the full permission set granted by a role."""
    return set(_ROLE_PERMISSIONS.get(role, set()))


def role_has(role: Role, permission: Permission) -> bool:
    """True iff ``role`` grants ``permission``."""
    return permission in _ROLE_PERMISSIONS.get(role, set())


# ───────────────────────────── Tiers ────────────────────────────────────
# Commercial plans. These gate *features and quotas*, independent of role.
# A Personal account has an Owner too — but that Owner cannot use SSO.

class Tier(str, Enum):
    PERSONAL = "personal"      # individuals: protect your own name/domain/handles
    PRO = "pro"                # solo professionals / creators / small sellers
    BUSINESS = "business"      # SMB teams
    ENTERPRISE = "enterprise"  # large orgs: SSO, SCIM, residency, CMK


class Feature(str, Enum):
    SSO = "sso"
    SCIM = "scim"
    MFA_ENFORCED = "mfa_enforced"          # org can *require* MFA for all members
    MULTI_REGION_CLOAK = "multi_region_cloak"
    SCHEDULED_REPORTS = "scheduled_reports"
    BOARD_PACK = "board_pack"
    EMAIL_ALERTS = "email_alerts"
    WEBHOOK_DELIVERY = "webhook_delivery"
    AUTO_TAKEDOWN_SUBMIT = "auto_takedown_submit"  # submit after human approval, no second gate
    CUSTOM_KMS = "custom_kms"              # customer-managed encryption keys
    DATA_RESIDENCY = "data_residency"
    AUDIT_EXPORT = "audit_export"
    PRIORITY_SUPPORT = "priority_support"


# Quotas per tier. ``None`` means unlimited (Enterprise).
class TierLimits:
    def __init__(
        self,
        max_brands: int | None,
        max_members: int | None,
        daily_inspect_cap: int | None,
        review_sla_hours: int,
        features: set[Feature],
    ) -> None:
        self.max_brands = max_brands
        self.max_members = max_members
        self.daily_inspect_cap = daily_inspect_cap
        self.review_sla_hours = review_sla_hours
        self.features = features


_TIER_LIMITS: dict[Tier, TierLimits] = {
    Tier.PERSONAL: TierLimits(
        max_brands=1, max_members=1, daily_inspect_cap=50, review_sla_hours=72,
        features={Feature.EMAIL_ALERTS},
    ),
    Tier.PRO: TierLimits(
        max_brands=3, max_members=3, daily_inspect_cap=300, review_sla_hours=48,
        features={
            Feature.EMAIL_ALERTS, Feature.MFA_ENFORCED, Feature.SCHEDULED_REPORTS,
            Feature.WEBHOOK_DELIVERY,
        },
    ),
    Tier.BUSINESS: TierLimits(
        max_brands=25, max_members=25, daily_inspect_cap=2000, review_sla_hours=24,
        features={
            Feature.EMAIL_ALERTS, Feature.MFA_ENFORCED, Feature.SCHEDULED_REPORTS,
            Feature.WEBHOOK_DELIVERY, Feature.MULTI_REGION_CLOAK, Feature.BOARD_PACK,
            Feature.AUDIT_EXPORT, Feature.AUTO_TAKEDOWN_SUBMIT,
        },
    ),
    Tier.ENTERPRISE: TierLimits(
        max_brands=None, max_members=None, daily_inspect_cap=None, review_sla_hours=8,
        features={f for f in Feature},  # everything
    ),
}


def limits_for(tier: Tier) -> TierLimits:
    return _TIER_LIMITS[tier]


def tier_has_feature(tier: Tier, feature: Feature) -> bool:
    return feature in _TIER_LIMITS[tier].features


__all__ = [
    "Permission", "Role", "Tier", "Feature", "TierLimits",
    "permissions_for", "role_has", "limits_for", "tier_has_feature",
]
