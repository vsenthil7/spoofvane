"""
Tenant model.

A Tenant is the top-level organisational unit. Every Brand belongs to a
Tenant; every Alert is scoped to a Tenant via the Brand it came from. This
file defines the Tenant pydantic model used across the API + storage layers.

In the prototype Tenants are managed by the platform operator (us). In
production this would be self-serve signup + admin-invite, with billing,
plan limits, and per-tenant quotas attached. Those concerns are deliberately
out of scope here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TenantPlan(str, Enum):
    """Billing plan tier — affects rate limits and quotas."""

    TRIAL = "trial"
    STANDARD = "standard"  # mid-market, 1 brand
    ENTERPRISE = "enterprise"  # multi-brand, multi-region
    OEM = "oem"  # licence partner reselling our engine


class Tenant(BaseModel):
    """An organisation that uses DoppelDomain."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    plan: TenantPlan = TenantPlan.TRIAL
    # Daily quota for Bright Data spend in USD. None = unlimited.
    daily_spend_cap_usd: float | None = None
    # Max suspect URLs inspected per day. None = unlimited.
    daily_inspect_cap: int | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class ApiKey(BaseModel):
    """An API key issued to a tenant.

    Keys carry scopes which restrict what they can do — read-only keys for
    SIEM integrations, brand-scoped keys for per-brand integrations, etc.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str  # public id, used in API requests
    tenant_id: str
    name: str  # human-readable label
    scopes: list[str] = Field(default_factory=list)
    # We store only a SHA-256 of the secret; the secret itself is shown once
    # at creation time and never displayed again.
    secret_hash: str
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    @property
    def is_active(self) -> bool:
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < _utcnow():
            return False
        return True


# Standard scope names. These map 1:1 to API surfaces; a key carrying
# "alerts:read" can call GET /api/alerts but not POST. A key with
# "brand:demobank-1" is restricted to that brand id.
SCOPE_ALERTS_READ = "alerts:read"
SCOPE_ALERTS_TRIAGE = "alerts:triage"
SCOPE_BRANDS_READ = "brands:read"
SCOPE_BRANDS_WRITE = "brands:write"
SCOPE_DISCOVERY_RUN = "discovery:run"
SCOPE_ADMIN = "admin:*"

ALL_SCOPES = (
    SCOPE_ALERTS_READ,
    SCOPE_ALERTS_TRIAGE,
    SCOPE_BRANDS_READ,
    SCOPE_BRANDS_WRITE,
    SCOPE_DISCOVERY_RUN,
    SCOPE_ADMIN,
)


def key_satisfies(key_scopes: list[str], required: str) -> bool:
    """Return True iff ``key_scopes`` covers the ``required`` scope.

    The ``admin:*`` scope always wins. Brand-scoped keys (``brand:<id>``)
    only satisfy a brand-scoped requirement for the same id.
    """
    if SCOPE_ADMIN in key_scopes:
        return True
    return required in key_scopes
