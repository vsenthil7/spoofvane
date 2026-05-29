"""Authentication & account routes (v0.3).

Endpoints
---------
POST /auth/signup            self-serve account+owner creation
POST /auth/login             email+password -> JWT + session cookie (or MFA challenge)
POST /auth/mfa/verify        complete an MFA challenge
POST /auth/logout            revoke session + clear cookie
GET  /auth/me                current user + permissions
POST /auth/mfa/enroll        begin TOTP enrolment (returns provisioning URI)
POST /auth/mfa/confirm       confirm enrolment, returns recovery codes
GET  /auth/oidc/login        redirect to the IdP
GET  /auth/oidc/callback     handle IdP callback (JIT-provisions user)

Login issues BOTH a JWT (for API/SPA use, returned in body) and a signed
session cookie (for the server-rendered web UI). Either can authenticate
subsequent requests.
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from ..common import identity as idsvc
from ..common import security
from ..common.logging import get_logger
from ..common.rbac import Tier
from ..common.settings import get_settings
from ..storage.db import session_scope
from .deps import AuthedUser, current_user

log = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


# ───────────────────────────── Schemas ──────────────────────────────────

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = ""
    account_name: str | None = None
    tier: Tier = Tier.PERSONAL


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    account_id: str | None = None


class MfaVerifyIn(BaseModel):
    user_id: str
    code: str
    account_id: str | None = None


class MfaConfirmIn(BaseModel):
    code: str


def _set_session_cookie(response: Response, sid: str) -> None:
    settings = get_settings()
    token = security.sign_session({"sid": sid})
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "prod",
    )


def _tokens_for(au: AuthedUser) -> dict:
    return {
        "access_token": security.issue_access_token(
            user_id=au.user_id, account_id=au.account_id, role=au.role.value,
            tier=au.tier.value, email=au.email, full_name=au.full_name,
            is_platform_staff=au.is_platform_staff,
        ),
        "refresh_token": security.issue_refresh_token(
            user_id=au.user_id, account_id=au.account_id
        ),
        "token_type": "bearer",
    }


def _user_payload(au: AuthedUser) -> dict:
    return {
        "user_id": au.user_id,
        "email": au.email,
        "full_name": au.full_name,
        "account_id": au.account_id,
        "role": au.role.value,
        "tier": au.tier.value,
        "permissions": sorted(au.permissions),
        "is_platform_staff": au.is_platform_staff,
    }


# ───────────────────────────── Routes ───────────────────────────────────

@router.post("/signup", status_code=201)
async def signup(body: SignupIn, request: Request, response: Response) -> dict:
    with session_scope() as s:
        try:
            au = idsvc.signup(
                s, email=body.email, password=body.password,
                full_name=body.full_name, account_name=body.account_name,
                tier=body.tier,
            )
        except idsvc.AuthError as e:
            raise HTTPException(status_code=409, detail=str(e))
        sid = idsvc.create_web_session(
            s, au, ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        out = {**_tokens_for(au), "user": _user_payload(au)}
    _set_session_cookie(response, sid)
    return out


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response) -> dict:
    with session_scope() as s:
        try:
            au = idsvc.authenticate_password(
                s, email=body.email, password=body.password, account_id=body.account_id
            )
        except idsvc.MfaRequired as e:
            return {"mfa_required": True, "user_id": e.user_id}
        except idsvc.AuthError as e:
            raise HTTPException(status_code=401, detail=str(e))
        sid = idsvc.create_web_session(
            s, au, ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        out = {**_tokens_for(au), "user": _user_payload(au), "mfa_required": False}
    _set_session_cookie(response, sid)
    return out


@router.post("/mfa/verify")
async def mfa_verify(body: MfaVerifyIn, request: Request, response: Response) -> dict:
    with session_scope() as s:
        try:
            au = idsvc.complete_mfa(
                s, user_id=body.user_id, code=body.code, account_id=body.account_id
            )
        except idsvc.AuthError as e:
            raise HTTPException(status_code=401, detail=str(e))
        sid = idsvc.create_web_session(
            s, au, ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"), mfa_satisfied=True,
        )
        out = {**_tokens_for(au), "user": _user_payload(au)}
    _set_session_cookie(response, sid)
    return out


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    settings = get_settings()
    raw = request.cookies.get(settings.session_cookie_name)
    if raw:
        payload = security.load_session(raw)
        if payload and "sid" in payload:
            with session_scope() as s:
                idsvc.revoke_web_session(s, payload["sid"])
    response.delete_cookie(settings.session_cookie_name)
    return {"ok": True}


@router.get("/me")
async def me(user: AuthedUser = Depends(current_user)) -> dict:
    return _user_payload(user)


@router.post("/mfa/enroll")
async def mfa_enroll(user: AuthedUser = Depends(current_user)) -> dict:
    with session_scope() as s:
        return idsvc.begin_mfa_enrolment(s, user_id=user.user_id)


@router.post("/mfa/confirm")
async def mfa_confirm(body: MfaConfirmIn, user: AuthedUser = Depends(current_user)) -> dict:
    with session_scope() as s:
        try:
            codes = idsvc.confirm_mfa(s, user_id=user.user_id, code=body.code)
        except idsvc.AuthError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"enabled": True, "recovery_codes": codes}


# ─────────────────────────────── OIDC ───────────────────────────────────
# Minimal, dependency-light OIDC Authorization-Code flow. Uses Authlib only
# for discovery + token parsing; state is signed so we don't need server
# storage. Works with Google, Okta, Entra ID, Auth0, etc.

_OIDC_STATE_SALT = "spoofvane.oidc.state.v1"


@router.get("/oidc/login")
async def oidc_login() -> dict:
    settings = get_settings()
    if not settings.oidc_enabled or not settings.oidc_issuer:
        raise HTTPException(status_code=404, detail="OIDC not configured")
    import httpx
    from itsdangerous import URLSafeTimedSerializer

    disc = httpx.get(f"{settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration",
                     timeout=10).json()
    state = URLSafeTimedSerializer(settings.secret_key, salt=_OIDC_STATE_SALT).dumps(
        {"n": secrets.token_urlsafe(8)}
    )
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_url,
        "scope": settings.oidc_scopes,
        "state": state,
    }
    auth_url = disc["authorization_endpoint"] + "?" + "&".join(
        f"{k}={httpx.QueryParams({k: v})[k]}" for k, v in params.items()
    )
    return {"authorization_url": auth_url}


@router.get("/oidc/callback")
async def oidc_callback(request: Request, response: Response, code: str, state: str) -> dict:
    settings = get_settings()
    if not settings.oidc_enabled:
        raise HTTPException(status_code=404, detail="OIDC not configured")
    import httpx
    from itsdangerous import BadSignature, URLSafeTimedSerializer

    try:
        URLSafeTimedSerializer(settings.secret_key, salt=_OIDC_STATE_SALT).loads(
            state, max_age=600
        )
    except BadSignature:
        raise HTTPException(status_code=400, detail="invalid OIDC state")

    disc = httpx.get(f"{settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration",
                     timeout=10).json()
    tok = httpx.post(disc["token_endpoint"], data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.oidc_redirect_url,
        "client_id": settings.oidc_client_id,
        "client_secret": settings.oidc_client_secret,
    }, timeout=10).json()

    userinfo = httpx.get(
        disc["userinfo_endpoint"],
        headers={"Authorization": f"Bearer {tok['access_token']}"}, timeout=10
    ).json()

    with session_scope() as s:
        au = idsvc.upsert_oidc_user(
            s, issuer=settings.oidc_issuer, subject=userinfo["sub"],
            email=userinfo.get("email", ""), full_name=userinfo.get("name", ""),
        )
        sid = idsvc.create_web_session(
            s, au, ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"), mfa_satisfied=True,
        )
        out = {**_tokens_for(au), "user": _user_payload(au)}
    _set_session_cookie(response, sid)
    return out


__all__ = ["router"]
