"""FastAPI auth dependencies — the single gate every protected route uses.

Resolves a request to an :class:`AuthedUser` from *either*:

* an ``Authorization: Bearer <jwt>`` header (API clients, SPA, mobile), or
* the signed session cookie (server-rendered web UI).

Then optionally enforces a required :class:`Permission` (RBAC) and/or a
required :class:`Feature` (commercial tier gate). Both must pass.

Usage in a router::

    @router.get("/alerts", dependencies=[Depends(require(Permission.ALERTS_READ))])
    async def list_alerts(user: AuthedUser = Depends(current_user)):
        ...

Backward compatibility: the legacy API-key dependency in ``src/api/auth.py``
still works for existing integrations; this module is additive.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError

from ..common import security
from ..common.identity import AuthedUser, load_web_session
from ..common.rbac import Feature, Permission, Role, Tier, permissions_for, tier_has_feature
from ..common.settings import get_settings
from ..storage.db import session_scope


def _from_bearer(token: str) -> AuthedUser | None:
    try:
        claims = security.decode_token(token, expected_type="access")
    except JWTError:
        return None
    return AuthedUser(
        user_id=claims["sub"],
        email=claims.get("email", ""),
        full_name=claims.get("name", ""),
        account_id=claims["account_id"],
        role=Role(claims["role"]),
        tier=Tier(claims.get("tier", "business")),
        is_platform_staff=bool(claims.get("staff", False)),
    )


def _from_cookie(request: Request) -> AuthedUser | None:
    settings = get_settings()
    raw = request.cookies.get(settings.session_cookie_name)
    if not raw:
        return None
    payload = security.load_session(
        raw, max_age_seconds=settings.session_max_age_hours * 3600
    )
    if not payload or "sid" not in payload:
        return None
    with session_scope() as s:
        return load_web_session(s, payload["sid"])


async def current_user(request: Request) -> AuthedUser:
    """Resolve the caller. Raises 401 if neither token nor session is valid."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        user = _from_bearer(auth[7:].strip())
        if user is not None:
            return user
    user = _from_cookie(request)
    if user is not None:
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def optional_user(request: Request) -> AuthedUser | None:
    """Like :func:`current_user` but returns ``None`` instead of raising.

    Used by the web UI so pages can render a login prompt rather than 401.
    """
    try:
        return await current_user(request)
    except HTTPException:
        return None


def require(*required: Permission):
    """Dependency factory enforcing that the caller's role grants all perms."""

    async def _dep(user: AuthedUser = Depends(current_user)) -> AuthedUser:
        granted = permissions_for(user.role)
        missing = [p for p in required if p not in granted]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing permission(s): {', '.join(p.value for p in missing)}",
            )
        return user

    return _dep


def require_feature(feature: Feature):
    """Dependency enforcing that the caller's account tier includes a feature."""

    async def _dep(user: AuthedUser = Depends(current_user)) -> AuthedUser:
        if not tier_has_feature(user.tier, feature):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"feature '{feature.value}' requires a higher plan "
                       f"(current: {user.tier.value})",
            )
        return user

    return _dep


def require_platform_staff():
    async def _dep(user: AuthedUser = Depends(current_user)) -> AuthedUser:
        if not user.is_platform_staff:
            raise HTTPException(status_code=403, detail="platform staff only")
        return user

    return _dep


__all__ = [
    "current_user", "optional_user", "require", "require_feature",
    "require_platform_staff",
]
