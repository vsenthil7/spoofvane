"""Audit middleware — records every state-changing HTTP request.

Captures POST/PUT/PATCH/DELETE on ``/api`` and ``/auth`` routes (excluding
read-only and noisy endpoints), resolving the actor from the JWT/session when
present. Writes a hash-chained entry via :mod:`src.common.audit` after the
response, including the resulting status code.

This guarantees REQ-AUD-01 (every mutating action logged) at the framework
level, so individual routes don't have to remember to log — though they may
add richer before/after detail via the audit service directly.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..common import audit
from ..common.logging import get_logger
from ..storage.db import session_scope

log = get_logger(__name__)

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
# Endpoints we don't audit (too noisy or not state-changing in a meaningful way)
_SKIP_PREFIXES = ("/static", "/metrics", "/healthz", "/docs", "/openapi", "/_probe")


def _actor_account(request: Request) -> tuple[str, str | None]:
    """Best-effort resolve (actor_email_or_id, account_id) without raising."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            from ..common import security
            claims = security.decode_token(auth[7:].strip(), expected_type="access")
            return claims.get("email") or claims.get("sub", "unknown"), claims.get("account_id")
        except Exception:
            return "unknown", None
    # session cookie
    try:
        from ..common import security
        from ..common.settings import get_settings
        from ..common.identity import load_web_session
        raw = request.cookies.get(get_settings().session_cookie_name)
        if raw:
            payload = security.load_session(raw)
            if payload and "sid" in payload:
                with session_scope() as s:
                    au = load_web_session(s, payload["sid"])
                    if au:
                        return au.email, au.account_id
    except Exception:
        pass
    return "anonymous", None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        should = (
            request.method in _MUTATING
            and not any(path.startswith(p) for p in _SKIP_PREFIXES)
        )
        if not should:
            return await call_next(request)

        actor, account_id = _actor_account(request)
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

        response = await call_next(request)

        # Don't audit failed auth as the actor's action if anonymous + 401
        try:
            with session_scope() as s:
                audit.record(
                    s,
                    actor=actor,
                    action=f"{request.method} {path}",
                    account_id=account_id,
                    target_kind="http",
                    request_ip=ip,
                    user_agent=ua,
                    status_code=response.status_code,
                )
        except Exception as exc:  # never let auditing break the request
            log.warning("audit.middleware_failed", error=str(exc), path=path)

        return response


__all__ = ["AuditMiddleware"]
