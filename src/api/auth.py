"""
API key authentication dependency for FastAPI.

Clients authenticate by sending an HTTP header::

    Authorization: ApiKey <key_id>:<secret>

The dependency parses the header, looks up the key, checks the secret with
constant-time comparison, verifies the key is active (not revoked, not
expired), and returns the matched ApiKey + Tenant pair. Routes that need
auth declare ``ctx: AuthCtx = Depends(require_auth())`` and FastAPI handles
the rest.

For routes scoped to a particular permission, pass scopes to
``require_auth("alerts:triage")`` — the dependency raises 403 if the key
doesn't carry that scope (or ``admin:*``).

The platform-operator default is a single anonymous tenant for backward
compatibility with existing test clients. Set ``REQUIRE_AUTH=true`` to flip
to strict mode where every API call must present a valid key.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from ..common.logging import get_logger
from ..common.settings import get_settings
from ..common.tenants import ApiKey, Tenant, key_satisfies
from ..storage.db import session_scope
from ..storage.repositories_v2 import ApiKeyRepo, TenantRepo

logger = get_logger(__name__)


@dataclass(slots=True)
class AuthCtx:
    """The principal that made an authenticated request."""

    api_key: ApiKey | None  # None when REQUIRE_AUTH=false and no key was sent
    tenant: Tenant | None
    actor: str  # used in audit log; e.g. "apikey:dd_xxx" or "anonymous"


def _parse_authorization(header: str | None) -> tuple[str, str] | None:
    if not header:
        return None
    parts = header.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "apikey":
        return None
    if ":" not in parts[1]:
        return None
    key_id, secret = parts[1].split(":", 1)
    return key_id.strip(), secret.strip()


def require_auth(*required_scopes: str):
    """Return a FastAPI dependency that enforces auth with optional scopes.

    Usage::

        @app.get("/api/alerts")
        def list_alerts(ctx: AuthCtx = Depends(require_auth("alerts:read"))):
            ...
    """

    def _dep(authorization: str | None = Header(default=None)) -> AuthCtx:
        settings = get_settings()
        parsed = _parse_authorization(authorization)

        # When REQUIRE_AUTH is off and the caller didn't send a key, allow
        # through as anonymous (legacy / single-tenant deploys, tests).
        require_auth_flag = getattr(settings, "require_auth", False)
        if parsed is None:
            if require_auth_flag:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Authorization header",
                    headers={"WWW-Authenticate": "ApiKey"},
                )
            return AuthCtx(api_key=None, tenant=None, actor="anonymous")

        key_id, secret = parsed
        with session_scope() as s:
            key = ApiKeyRepo(s).authenticate(key_id, secret)
            if key is None:
                logger.warning("auth.failed", key_id=key_id)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "ApiKey"},
                )
            tenant = TenantRepo(s).get(key.tenant_id)

        # Scope enforcement
        for scope in required_scopes:
            if not key_satisfies(key.scopes, scope):
                logger.warning(
                    "auth.scope_denied", key_id=key.id, required=scope, has=key.scopes
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scope: {scope}",
                )

        return AuthCtx(api_key=key, tenant=tenant, actor=f"apikey:{key.id}")

    return _dep
