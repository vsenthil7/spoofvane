"""Security primitives: password hashing, JWT, TOTP MFA, signed sessions.

Kept dependency-light and side-effect-free so it can be unit-tested without a
running app. All secrets come from settings; nothing is hard-coded.

* **Passwords** — bcrypt via ``bcrypt`` directly (no passlib indirection, which
  has a known version-detection wart). Bcrypt's 72-byte input limit is handled
  explicitly by pre-hashing long inputs with SHA-256.
* **JWT** — short-lived access tokens + longer refresh tokens, HS256.
* **TOTP** — RFC-6238 via ``pyotp``; provisioning URI + QR for enrolment.
* **Sessions** — ``itsdangerous`` signed cookies for the server-rendered web UI.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import pyotp
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from jose import JWTError, jwt

from .settings import get_settings


# ───────────────────────────── Passwords ────────────────────────────────

def _prehash(password: str) -> bytes:
    """Reduce arbitrary-length input to a fixed 32 bytes before bcrypt.

    Bcrypt silently truncates anything past 72 bytes, which is a subtle
    security footgun (two different long passwords can collide). Pre-hashing
    with SHA-256 and base64-encoding keeps us comfortably under the limit and
    removes the footgun. Base64 of 32 bytes is 44 chars — well under 72.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    """Return a bcrypt hash string for ``password``."""
    if not password or len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time check of ``password`` against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(_prehash(password), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


# ─────────────────────────────── JWT ────────────────────────────────────

_ACCESS_TTL = timedelta(minutes=30)
_REFRESH_TTL = timedelta(days=14)
_ALGO = "HS256"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _encode(claims: dict[str, Any], ttl: timedelta, token_type: str) -> str:
    settings = get_settings()
    payload = {
        **claims,
        "type": token_type,
        "iat": int(_now().timestamp()),
        "exp": int((_now() + ttl).timestamp()),
        "jti": secrets.token_urlsafe(8),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGO)


def issue_access_token(
    *, user_id: str, account_id: str, role: str,
    tier: str = "business", email: str = "", full_name: str = "",
    is_platform_staff: bool = False,
) -> str:
    return _encode(
        {
            "sub": user_id, "account_id": account_id, "role": role,
            "tier": tier, "email": email, "name": full_name,
            "staff": is_platform_staff,
        },
        _ACCESS_TTL, "access",
    )


def issue_refresh_token(*, user_id: str, account_id: str) -> str:
    return _encode({"sub": user_id, "account_id": account_id}, _REFRESH_TTL, "refresh")


def decode_token(token: str, *, expected_type: str | None = None) -> dict[str, Any]:
    """Decode + verify a JWT. Raises ``JWTError`` on any problem."""
    settings = get_settings()
    payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGO])
    if expected_type is not None and payload.get("type") != expected_type:
        raise JWTError(f"expected {expected_type} token, got {payload.get('type')}")
    return payload


# ─────────────────────────────── TOTP MFA ───────────────────────────────

def new_mfa_secret() -> str:
    """Return a fresh base32 TOTP secret to store (encrypted) per user."""
    return pyotp.random_base32()


def mfa_provisioning_uri(secret: str, *, account_name: str, issuer: str = "DoppelDomain") -> str:
    """``otpauth://`` URI for QR enrolment in Google Authenticator / Authy."""
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=issuer)


def verify_totp(secret: str, code: str, *, valid_window: int = 1) -> bool:
    """Verify a 6-digit TOTP code, tolerating ±1 step of clock drift."""
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=valid_window)


def new_recovery_codes(n: int = 10) -> list[str]:
    """Generate one-time MFA recovery codes (store hashed, show once)."""
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(n)]


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def verify_recovery_code(code: str, hashed_list: list[str]) -> bool:
    target = hash_recovery_code(code.strip())
    return any(hmac.compare_digest(target, h) for h in hashed_list)


# ──────────────────────────── Web sessions ──────────────────────────────

_SESSION_SALT = "doppeldomain.web.session.v1"


def _session_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt=_SESSION_SALT)


def sign_session(data: dict[str, Any]) -> str:
    """Serialise + sign a session payload for a cookie."""
    return _session_serializer().dumps(data)


def load_session(token: str, *, max_age_seconds: int = 60 * 60 * 12) -> dict[str, Any] | None:
    """Load a signed session cookie, or ``None`` if invalid/expired."""
    try:
        return _session_serializer().loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None


# ─────────────────────── API-key secret hashing ─────────────────────────
# (kept here so the existing api_keys table can share one hashing scheme)

def hash_api_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def new_api_secret() -> str:
    return "dd_" + secrets.token_urlsafe(32)


__all__ = [
    "hash_password", "verify_password",
    "issue_access_token", "issue_refresh_token", "decode_token",
    "new_mfa_secret", "mfa_provisioning_uri", "verify_totp",
    "new_recovery_codes", "hash_recovery_code", "verify_recovery_code",
    "sign_session", "load_session",
    "hash_api_secret", "new_api_secret",
]
