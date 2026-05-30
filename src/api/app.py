"""
SpoofVane HTTP API + triage dashboard.

This module exposes a single :class:`fastapi.FastAPI` instance named ``app``
which can be served by ``uvicorn``::

    uvicorn src.api.app:app --reload

It bundles three surfaces:

1. **REST endpoints** under ``/api/...`` — used by automation and by the
   in-page JavaScript on the dashboard.
2. **HTML dashboard** at ``/`` — server-rendered Jinja templates so it works
   without a separate frontend build step.
3. **Evidence-pack PDF download** at ``/api/alerts/{id}/evidence.pdf``.

All persistence goes through the repositories in ``src.storage.repositories``;
this layer is intentionally thin — request validation, response shaping, and
nothing else.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, Body, Depends, FastAPI, HTTPException, Path as PathParam, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, HttpUrl

from ..common.ids import brand_id as gen_brand_id
from ..common.logging import get_logger
from ..common.models import Alert, AlertStatus, Brand, SuspectURL, Verdict
from ..common.pipeline import PipelineStats, run_pipeline_for_brand
from ..common.settings import get_settings
from ..common.tenants import (
    SCOPE_ALERTS_READ,
    SCOPE_ALERTS_TRIAGE,
    SCOPE_BRANDS_READ,
    SCOPE_BRANDS_WRITE,
    SCOPE_DISCOVERY_RUN,
)
from ..delivery.pdf_evidence import build_evidence_pdf
from ..storage.db import session_scope
from ..storage.repositories import (
    AlertRepo,
    BrandRepo,
    InspectionRepo,
    ScoringRepo,
    SuspectURLRepo,
    VerdictRepo,
)
from ..storage.repositories_v2 import AuditLogRepo, FeedbackEventRepo
from .auth import AuthCtx, require_auth

logger = get_logger(__name__)
settings = get_settings()

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

_HERE = Path(__file__).resolve().parent
_WEB_DIR = _HERE.parent / "web"
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


# --------------------------------------------------------------------------- #
# Schemas (request / response only — domain models live in common.models)
# --------------------------------------------------------------------------- #


class BrandCreate(BaseModel):
    """Payload to onboard a brand."""

    name: str = Field(min_length=1, max_length=120)
    login_url: HttpUrl
    payment_url: HttpUrl | None = None
    target_country: str = Field(default="US", min_length=2, max_length=2)
    brand_keywords: list[str] = Field(default_factory=list)
    score_threshold: float = Field(default=0.65, ge=0.0, le=1.0)


class DiscoveryRunRequest(BaseModel):
    brand_id: str
    sources: list[str] | None = None
    max_inspect: int = Field(default=25, ge=1, le=200)


class TriageRequest(BaseModel):
    status: AlertStatus
    notes: str | None = None
    triaged_by: str = Field(min_length=1, max_length=120)


class AlertNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    author: str | None = Field(default=None, max_length=200)


# --------------------------------------------------------------------------- #
# App + templates
# --------------------------------------------------------------------------- #

app = FastAPI(
    title="SpoofVane",
    version="0.3.0",
    description=(
        "Brand-impersonation detection — Bright Data Hackathon Track 3. "
        "Catches phishing infrastructure by fingerprinting the rendered page, "
        "not just the domain name."
    ),
)

# Tenant + API key + cost-attribution admin endpoints
from .admin_router import router as admin_router  # noqa: E402
app.include_router(admin_router)

# Identity, login, MFA, OIDC (v0.3)
from .auth_router import router as auth_router  # noqa: E402
app.include_router(auth_router)

# Human-in-the-loop review, notifications, reports, audit (v0.3 Phases 2–5)
from .ops_router import router as ops_router  # noqa: E402
app.include_router(ops_router)

# Audit middleware — records every mutating request (hash-chained)
from .audit_middleware import AuditMiddleware  # noqa: E402
app.add_middleware(AuditMiddleware)

# Static + templates
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    """Liveness probe used by demo runner / k8s."""
    return {"status": "ok", "mock_mode": str(settings.mock_mode).lower()}


@app.get("/metrics", tags=["meta"])
def metrics() -> Response:
    """Prometheus metrics exposition. Gated by PROMETHEUS_ENABLED."""
    if not getattr(settings, "prometheus_enabled", True):
        raise HTTPException(404, "Metrics disabled")
    from src.api.metrics import render_metrics
    return Response(content=render_metrics(), media_type="text/plain; version=0.0.4")


# --------------------------------------------------------------------------- #
# Brands
# --------------------------------------------------------------------------- #


@app.post("/api/brands", tags=["brands"], status_code=201)
def create_brand(
    payload: BrandCreate,
    request: Request,
    ctx: AuthCtx = Depends(require_auth(SCOPE_BRANDS_WRITE)),
) -> dict:
    """Onboard a new brand. Canonical assets are added later via the onboard
    script, since they require an inspection pass against the real login URL."""
    brand = Brand(
        id=gen_brand_id(),
        name=payload.name,
        login_url=payload.login_url,
        payment_url=payload.payment_url,
        target_country=payload.target_country.upper(),
        brand_keywords=payload.brand_keywords,
        score_threshold=payload.score_threshold,
        tenant_id=(ctx.tenant.id if ctx.tenant else None),
    )
    with session_scope() as s:
        repo = BrandRepo(s)
        if repo.get_by_name(brand.name) is not None:
            raise HTTPException(409, f"Brand already exists: {brand.name}")
        brand = repo.create(brand)
        AuditLogRepo(s).record(
            actor=ctx.actor,
            action="brand.create",
            tenant_id=brand.tenant_id,
            target_kind="brand",
            target_id=brand.id,
            after=brand.model_dump(mode="json"),
            request_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    return brand.model_dump(mode="json")


@app.get("/api/brands", tags=["brands"])
def list_brands(
    ctx: AuthCtx = Depends(require_auth(SCOPE_BRANDS_READ)),
) -> list[dict]:
    with session_scope() as s:
        tenant_id = ctx.tenant.id if ctx.tenant else None
        brands = BrandRepo(s).list_all(tenant_id=tenant_id)
    return [b.model_dump(mode="json") for b in brands]


@app.get("/api/brands/{brand_id}", tags=["brands"])
def get_brand(
    brand_id: Annotated[str, PathParam(min_length=1)],
    ctx: AuthCtx = Depends(require_auth(SCOPE_BRANDS_READ)),
) -> dict:
    with session_scope() as s:
        brand = BrandRepo(s).get(brand_id)
    if brand is None:
        raise HTTPException(404, f"Brand not found: {brand_id}")
    # Tenant isolation: a non-admin key cannot see another tenant's brands
    if ctx.tenant is not None and brand.tenant_id and brand.tenant_id != ctx.tenant.id:
        raise HTTPException(404, f"Brand not found: {brand_id}")
    return brand.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# Discovery + pipeline
# --------------------------------------------------------------------------- #


@app.post("/api/discovery/run", tags=["pipeline"])
def run_discovery(
    payload: DiscoveryRunRequest,
    background: BackgroundTasks,
    request: Request,
    wait: bool = Query(default=False, description="Block until pipeline completes"),
    ctx: AuthCtx = Depends(require_auth(SCOPE_DISCOVERY_RUN)),
) -> dict:
    """Kick off discovery → inspection → scoring → verdict for a brand.

    By default this returns immediately and the pipeline runs in a background
    task. For the demo (and for tests) set ``?wait=true`` to block and return
    the stats inline.
    """
    with session_scope() as s:
        brand = BrandRepo(s).get(payload.brand_id)
        if brand is None:
            raise HTTPException(404, f"Brand not found: {payload.brand_id}")
        # Tenant isolation
        if ctx.tenant is not None and brand.tenant_id and brand.tenant_id != ctx.tenant.id:
            raise HTTPException(404, f"Brand not found: {payload.brand_id}")
        AuditLogRepo(s).record(
            actor=ctx.actor,
            action="discovery.run",
            tenant_id=brand.tenant_id,
            target_kind="brand",
            target_id=brand.id,
            after={"sources": payload.sources, "max_inspect": payload.max_inspect, "wait": wait},
            request_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

    if wait:
        stats = run_pipeline_for_brand(
            payload.brand_id,
            sources=payload.sources,
            max_inspect=payload.max_inspect,
        )
        return {"status": "completed", "stats": _stats_dict(stats)}

    background.add_task(
        run_pipeline_for_brand,
        payload.brand_id,
        sources=payload.sources,
        max_inspect=payload.max_inspect,
    )
    return {"status": "queued", "brand_id": payload.brand_id}


@app.post("/api/discovery/recheck", tags=["pipeline"])
def recheck_brand(
    payload: DiscoveryRunRequest,
    request: Request,
    max_urls: int = Query(default=50, ge=1, le=500),
    hours_lookback: int = Query(default=48, ge=1, le=720),
    ctx: AuthCtx = Depends(require_auth(SCOPE_DISCOVERY_RUN)),
) -> dict:
    """Re-inspect recently-seen URLs to catch time-bomb phishing activations.

    A URL that rendered as a benign holding page on first pass but now serves
    a credential-harvest payload is a high-confidence time-bomb activation —
    the operator flipped it after distributing the link to victims. Single-shot
    scanners miss this entirely; this is the catch.
    """
    from src.inspection.diff_detector import recheck_recent

    with session_scope() as s:
        brand = BrandRepo(s).get(payload.brand_id)
        if brand is None:
            raise HTTPException(404, f"Brand not found: {payload.brand_id}")
        if ctx.tenant is not None and brand.tenant_id and brand.tenant_id != ctx.tenant.id:
            raise HTTPException(404, f"Brand not found: {payload.brand_id}")
        AuditLogRepo(s).record(
            actor=ctx.actor,
            action="discovery.recheck",
            tenant_id=brand.tenant_id,
            target_kind="brand",
            target_id=brand.id,
            after={"max_urls": max_urls, "hours_lookback": hours_lookback},
            request_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

    diffs = recheck_recent(payload.brand_id, max_urls=max_urls, hours_lookback=hours_lookback)
    time_bombs = [d for d in diffs if d.time_bomb]
    return {
        "status": "completed",
        "brand_id": payload.brand_id,
        "rechecked": len(diffs),
        "time_bombs_detected": len(time_bombs),
        "diffs": [
            {
                "suspect_url_id": d.suspect_url_id,
                "phash_change": d.phash_change,
                "dom_change": d.dom_change,
                "max_change": d.max_change,
                "looks_like_phish_now": d.looks_like_phish_now,
                "benign_before": d.benign_before,
                "time_bomb": d.time_bomb,
                "detected_at": d.detected_at.isoformat(),
            }
            for d in diffs
        ],
    }


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #


@app.get("/api/alerts", tags=["alerts"])
def list_alerts(
    brand_id: str | None = Query(default=None),
    status: AlertStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_READ)),
) -> list[dict]:
    tenant_id = ctx.tenant.id if ctx.tenant else None
    with session_scope() as s:
        repo = AlertRepo(s)
        alerts = repo.list_for_brand(
            brand_id=brand_id, status=status, tenant_id=tenant_id, limit=limit
        )
    return [a.model_dump(mode="json") for a in alerts]


@app.get("/api/alerts/{alert_id}", tags=["alerts"])
def get_alert(
    alert_id: str,
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_READ)),
) -> dict:
    bundle = _load_alert_bundle(alert_id)
    # Tenant isolation
    if ctx.tenant is not None and bundle["alert"].tenant_id and bundle["alert"].tenant_id != ctx.tenant.id:
        raise HTTPException(404, f"Alert not found: {alert_id}")
    return {
        "alert": bundle["alert"].model_dump(mode="json"),
        "brand": bundle["brand"].model_dump(mode="json"),
        "inspection": bundle["inspection"].model_dump(mode="json"),
        "scoring": bundle["scoring"].model_dump(mode="json"),
        "verdict": bundle["verdict"].model_dump(mode="json"),
    }


@app.post("/api/alerts/{alert_id}/triage", tags=["alerts"])
def triage_alert(
    alert_id: str,
    payload: TriageRequest,
    request: Request,
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_TRIAGE)),
) -> dict:
    with session_scope() as s:
        repo = AlertRepo(s)
        existing = repo.get(alert_id)
        if existing is None:
            raise HTTPException(404, f"Alert not found: {alert_id}")
        if ctx.tenant is not None and existing.tenant_id and existing.tenant_id != ctx.tenant.id:
            raise HTTPException(404, f"Alert not found: {alert_id}")
        updated = repo.update_triage(
            alert_id,
            status=payload.status,
            notes=payload.notes,
            actor=payload.triaged_by,
        )

        # Record an active-learning feedback event if the analyst marked a
        # final outcome. open/triaging → no feedback; confirmed → tp; dismissed → fp.
        outcome_map = {
            AlertStatus.CONFIRMED: "true_positive",
            AlertStatus.DISMISSED: "false_positive",
        }
        outcome = outcome_map.get(payload.status)
        if outcome is not None:
            verdict = VerdictRepo(s).get(existing.verdict_id)
            scoring = ScoringRepo(s).get(existing.inspection_id)
            FeedbackEventRepo(s).record(
                alert_id=alert_id,
                outcome=outcome,
                actor=payload.triaged_by or ctx.actor,
                tenant_id=existing.tenant_id,
                brand_id=existing.brand_id,
                attack_family=verdict.attack_family if verdict else None,
                kit_match=verdict.kit_match if verdict else None,
                cloaking_detected=bool(verdict.cloaking_detected) if verdict else False,
                composite_score=scoring.composite_score if scoring else None,
                notes=payload.notes,
            )

        AuditLogRepo(s).record(
            actor=payload.triaged_by or ctx.actor,
            action="alert.triage",
            tenant_id=existing.tenant_id,
            target_kind="alert",
            target_id=alert_id,
            before={"status": existing.status.value},
            after={"status": payload.status.value, "notes": payload.notes},
            request_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    return updated.model_dump(mode="json")


@app.get("/api/alerts/{alert_id}/notes", tags=["alerts"])
def list_alert_notes(
    alert_id: str,
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_READ)),
) -> list[dict]:
    from src.storage.repositories_v2 import AlertNoteRepo
    with session_scope() as s:
        existing = AlertRepo(s).get(alert_id)
        if existing is None:
            raise HTTPException(404, f"Alert not found: {alert_id}")
        if ctx.tenant is not None and existing.tenant_id and existing.tenant_id != ctx.tenant.id:
            raise HTTPException(404, f"Alert not found: {alert_id}")
        return AlertNoteRepo(s).list_for_alert(alert_id)


@app.post("/api/alerts/{alert_id}/notes", tags=["alerts"], status_code=201)
def add_alert_note(
    alert_id: str,
    payload: AlertNoteCreate,
    request: Request,
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_TRIAGE)),
) -> dict:
    from src.storage.repositories_v2 import AlertNoteRepo
    with session_scope() as s:
        existing = AlertRepo(s).get(alert_id)
        if existing is None:
            raise HTTPException(404, f"Alert not found: {alert_id}")
        if ctx.tenant is not None and existing.tenant_id and existing.tenant_id != ctx.tenant.id:
            raise HTTPException(404, f"Alert not found: {alert_id}")
        note = AlertNoteRepo(s).add(
            alert_id=alert_id,
            author=payload.author or ctx.actor,
            body=payload.body,
            tenant_id=existing.tenant_id,
        )
        AuditLogRepo(s).record(
            actor=payload.author or ctx.actor,
            action="alert.note_add",
            tenant_id=existing.tenant_id,
            target_kind="alert",
            target_id=alert_id,
            after={"note_id": note["id"]},
            request_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    return note


@app.post("/api/alerts/{alert_id}/takedown", tags=["alerts"])
def submit_alert_takedown(
    alert_id: str,
    request: Request,
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_TRIAGE)),
) -> dict:
    """Submit a takedown request to the appropriate registrar / hosting provider.

    The request is built from the alert's stored evidence; submission goes
    to the first enabled provider whose ``supports()`` matches the host or
    registrar. In MOCK_MODE no real network call is made — a synthetic case
    id is returned so the workflow is demonstrable end-to-end.
    """
    # Import here to ensure providers register on first call
    from ..delivery.takedown import submit_takedown  # noqa: E402
    from ..delivery.takedown import cloudflare as _cf, namecheap as _nc, godaddy as _gd  # noqa: F401, E402

    bundle = _load_alert_bundle(alert_id)
    if ctx.tenant is not None and bundle["alert"].tenant_id and bundle["alert"].tenant_id != ctx.tenant.id:
        raise HTTPException(404, f"Alert not found: {alert_id}")

    result = submit_takedown(
        bundle["alert"], bundle["brand"], bundle["inspection"], bundle["verdict"]
    )

    with session_scope() as s:
        AuditLogRepo(s).record(
            actor=ctx.actor,
            action="takedown.submit",
            tenant_id=bundle["alert"].tenant_id,
            target_kind="alert",
            target_id=alert_id,
            after={
                "provider": result.provider,
                "success": result.success,
                "case_id": result.case_id,
                "error": result.error,
            },
            request_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    if not result.success:
        raise HTTPException(400, result.error or "Takedown submission failed")
    return {
        "alert_id": alert_id,
        "provider": result.provider,
        "case_id": result.case_id,
        "submitted_at": _utc_now_iso(),
    }


def _utc_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Audit log surface (read-only summary)
# --------------------------------------------------------------------------- #


@app.get("/api/audit-log", tags=["meta"])
def list_audit_log(
    actor: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_READ)),
) -> list[dict]:
    """Read the audit log scoped to the caller's tenant."""
    tenant_id = ctx.tenant.id if ctx.tenant else None
    with session_scope() as s:
        return AuditLogRepo(s).list_recent(
            tenant_id=tenant_id, actor=actor, action=action, limit=limit
        )


# --------------------------------------------------------------------------- #
# Console-facing read surfaces (consumed by the Flutter SOC console).
# These shape existing domain data into the flat objects the console renders, so
# the Clusters / Deepfakes / Cost screens run on LIVE backend data rather than
# the offline seed lane.
# --------------------------------------------------------------------------- #

_DEEPFAKE_FAMILIES = {"deepfake", "deepfake_rtc", "voice_clone", "voice-clone", "synthetic_media"}


def _alert_console_shape(
    alert: Alert,
    verdict: Verdict | None,
    scoring,
) -> dict:
    """Flatten an alert (+ its verdict/scoring) into the console Alert shape."""
    return {
        "id": alert.id,
        "brand_id": alert.brand_id,
        "url": alert.suspect_url,
        "verdict": (verdict.verdict.value if verdict else "suspicious"),
        "composite_score": (scoring.composite_score if scoring else 0.0),
        "family": (verdict.attack_family if verdict else None),
        "kit": (verdict.kit_match if verdict else None),
        "rendered_from": None,
        "discovered_at": alert.created_at.isoformat() if alert.created_at else "",
        "mitre_techniques": [],
    }


@app.get("/api/deepfakes", tags=["console"])
def list_deepfakes(
    limit: int = Query(default=50, ge=1, le=500),
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_READ)),
) -> list[dict]:
    """Alerts whose verdict attack-family is a deepfake/synthetic-media family."""
    tenant_id = ctx.tenant.id if ctx.tenant else None
    out: list[dict] = []
    with session_scope() as s:
        alerts = AlertRepo(s).list_for_brand(tenant_id=tenant_id, limit=limit)
        for a in alerts:
            verdict = VerdictRepo(s).get(a.verdict_id)
            fam = (verdict.attack_family or "").lower() if verdict else ""
            if fam in _DEEPFAKE_FAMILIES:
                scoring = ScoringRepo(s).get(a.inspection_id)
                out.append(_alert_console_shape(a, verdict, scoring))
    return out


@app.get("/api/clusters", tags=["console"])
def list_clusters(
    limit: int = Query(default=200, ge=1, le=1000),
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_READ)),
) -> list[dict]:
    """Campaign clusters built from current alerts via the threat-actor graph.

    Groups alerts that share infrastructure (shared verdict kit/family signals)
    into campaigns; falls back to one cluster per alert when the graph yields
    nothing. Shaped as the console Cluster object {id, members, risk}.
    """
    from ..graph.entity_model import Finding
    from ..graph.campaign_detector import detect_campaigns

    tenant_id = ctx.tenant.id if ctx.tenant else None
    findings: list[Finding] = []
    risk_by_alert: dict[str, float] = {}
    with session_scope() as s:
        alerts = AlertRepo(s).list_for_brand(tenant_id=tenant_id, limit=limit)
        for a in alerts:
            verdict = VerdictRepo(s).get(a.verdict_id)
            scoring = ScoringRepo(s).get(a.inspection_id)
            risk_by_alert[a.id] = scoring.composite_score if scoring else 0.0
            findings.append(
                Finding(
                    a.id,
                    domain=a.suspect_url,
                    kit_family=(verdict.attack_family if verdict else None),
                    cert_sha=(verdict.kit_match if verdict else None),
                )
            )
    campaigns = detect_campaigns(findings) if findings else []
    out: list[dict] = []
    for i, c in enumerate(campaigns, start=1):
        members = list(c.domains)
        # Campaign risk = max composite among its member alerts (by domain).
        member_ids = [f.finding_id for f in findings if f.domain in set(members)]
        risk = max((risk_by_alert.get(mid, 0.0) for mid in member_ids), default=0.0)
        out.append({"id": i, "members": members, "risk": round(risk, 4)})
    return out


@app.get("/api/cost", tags=["console"])
def list_cost(
    days: int = Query(default=30, ge=1, le=90),
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_READ)),
) -> list[dict]:
    """Bright Data spend by product for the caller's tenant, as console CostRows.

    When the caller is authenticated to a tenant, spend is scoped to it. In the
    no-auth dev/demo lane (no tenant on the context) this falls back to the most
    recently created tenant so the cost screen shows live demo data.
    """
    from datetime import datetime, timedelta, timezone
    from ..storage.repositories_v2 import CostEventRepo, TenantRepo

    since = datetime.now(timezone.utc) - timedelta(days=days)
    with session_scope() as s:
        tenant_id = ctx.tenant.id if ctx.tenant else None
        if tenant_id is None:
            tenants = TenantRepo(s).list_all()
            if not tenants:
                return []
            tenant_id = tenants[-1].id  # most-recently created (demo lane)
        breakdown = CostEventRepo(s).breakdown_for_tenant(tenant_id, since=since)
    return [{"product": k, "usd": round(v, 4)} for k, v in sorted(breakdown.items())]


@app.get(
    "/api/alerts/{alert_id}/evidence.pdf",
    tags=["alerts"],
    response_class=FileResponse,
)
def evidence_pdf(
    alert_id: str,
    ctx: AuthCtx = Depends(require_auth(SCOPE_ALERTS_READ)),
) -> FileResponse:
    bundle = _load_alert_bundle(alert_id)
    if ctx.tenant is not None and bundle["alert"].tenant_id and bundle["alert"].tenant_id != ctx.tenant.id:
        raise HTTPException(404, f"Alert not found: {alert_id}")
    out = build_evidence_pdf(
        bundle["alert"],
        bundle["brand"],
        bundle["inspection"],
        bundle["scoring"],
        bundle["verdict"],
    )
    return FileResponse(
        path=str(out),
        media_type="application/pdf",
        filename=out.name,
    )


# --------------------------------------------------------------------------- #
# HTML dashboard
# --------------------------------------------------------------------------- #


@app.get("/login", response_class=HTMLResponse, tags=["dashboard"])
def login_page(request: Request) -> HTMLResponse:
    """Server-rendered login page. Lists seeded demo users when present."""
    settings = get_settings()
    demo_users: list[dict] = []
    try:
        from src.common.demo_users import DEMO_USERS, DEMO_PASSWORD
        demo_users = DEMO_USERS
        demo_password = DEMO_PASSWORD
    except Exception:
        demo_password = ""
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "mock_mode": settings.mock_mode,
            "oidc_enabled": settings.oidc_enabled,
            "demo_users": demo_users,
            "demo_password": demo_password,
        },
    )


@app.get("/", response_class=HTMLResponse, tags=["dashboard"])
def dashboard(request: Request) -> HTMLResponse:
    with session_scope() as s:
        brands = BrandRepo(s).list_all()
        all_alerts: list[Alert] = []
        for b in brands:
            all_alerts.extend(AlertRepo(s).list_for_brand(b.id, limit=100))
        # Bulk-load verdict signals for the queue display
        alert_signals: dict[str, dict] = {}
        for a in all_alerts:
            v = VerdictRepo(s).get(a.verdict_id)
            if v is None:
                continue
            alert_signals[a.id] = {
                "attack_family": v.attack_family,
                "kit_match": v.kit_match,
                "cloaking_detected": v.cloaking_detected,
            }
    all_alerts.sort(key=lambda a: a.created_at, reverse=True)

    brand_lookup = {b.id: b for b in brands}
    family_counts: dict[str, int] = {}
    kit_counts: dict[str, int] = {}
    cloaking_total = 0
    for sig in alert_signals.values():
        if sig["attack_family"]:
            family_counts[sig["attack_family"]] = family_counts.get(sig["attack_family"], 0) + 1
        if sig["kit_match"]:
            kit_counts[sig["kit_match"]] = kit_counts.get(sig["kit_match"], 0) + 1
        if sig["cloaking_detected"]:
            cloaking_total += 1
    # Bright Data spend rollup across all brands (today + per-kind breakdown)
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    from sqlalchemy import func as _func, select as _select
    from src.storage.models import CostEventRow as _CostRow
    cost_today = 0.0
    cost_breakdown: dict[str, float] = {}
    with session_scope() as s:
        since = _dt.now(_tz.utc) - _td(days=7)
        rows = s.execute(
            _select(_CostRow.kind, _func.coalesce(_func.sum(_CostRow.usd_amount), 0.0))
            .where(_CostRow.occurred_at >= since)
            .group_by(_CostRow.kind)
        ).all()
        cost_breakdown = {kind: round(float(amt), 4) for kind, amt in rows}
        cost_today = round(sum(cost_breakdown.values()), 4)

    summary = {
        "total_alerts": len(all_alerts),
        "open": sum(1 for a in all_alerts if a.status == AlertStatus.OPEN),
        "critical": sum(1 for a in all_alerts if a.severity.value == "critical"),
        "high": sum(1 for a in all_alerts if a.severity.value == "high"),
        "cloaking": cloaking_total,
        "families": family_counts,
        "kits": kit_counts,
        "cost_7d_usd": cost_today,
        "cost_breakdown": cost_breakdown,
    }
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "brands": brands,
            "brands_json": [b.model_dump(mode="json") for b in brands],
            "alerts": all_alerts,
            "alert_signals": alert_signals,
            "brand_lookup": brand_lookup,
            "summary": summary,
            "mock_mode": settings.mock_mode,
        },
    )


@app.get("/alerts/{alert_id}", response_class=HTMLResponse, tags=["dashboard"])
def alert_detail(request: Request, alert_id: str) -> HTMLResponse:
    bundle = _load_alert_bundle(alert_id)
    from src.storage.repositories_v2 import AlertNoteRepo
    with session_scope() as s:
        notes = AlertNoteRepo(s).list_for_alert(alert_id)
    return templates.TemplateResponse(
        request,
        "alert_detail.html",
        {
            "alert": bundle["alert"],
            "brand": bundle["brand"],
            "inspection": bundle["inspection"],
            "scoring": bundle["scoring"],
            "verdict": bundle["verdict"],
            "notes": notes,
            "mock_mode": settings.mock_mode,
        },
    )


@app.get("/audit", response_class=HTMLResponse, tags=["dashboard"])
def audit_log_page(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> HTMLResponse:
    """Human-readable audit log surface. Filters by tenant/actor/action via query string."""
    tenant_id = request.query_params.get("tenant_id")
    actor = request.query_params.get("actor")
    action = request.query_params.get("action")
    with session_scope() as s:
        entries = AuditLogRepo(s).list_recent(
            tenant_id=tenant_id, actor=actor, action=action, limit=limit
        )
    return templates.TemplateResponse(
        request,
        "audit_log.html",
        {
            "entries": entries,
            "filter_tenant_id": tenant_id,
            "filter_actor": actor,
            "filter_action": action,
            "mock_mode": settings.mock_mode,
        },
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _stats_dict(stats: PipelineStats) -> dict:
    return {
        "brand_id": stats.brand_id,
        "suspects_discovered": stats.suspects_discovered,
        "suspects_inspected": stats.suspects_inspected,
        "suspects_above_threshold": stats.suspects_above_threshold,
        "alerts_created": stats.alerts_created,
        "errors": stats.errors,
    }


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _load_alert_bundle(alert_id: str) -> dict:
    """Load an alert with all related rows in one transaction."""
    with session_scope() as s:
        alert = AlertRepo(s).get(alert_id)
        if alert is None:
            raise HTTPException(404, f"Alert not found: {alert_id}")
        brand = BrandRepo(s).get(alert.brand_id)
        inspection = InspectionRepo(s).get(alert.inspection_id)
        scoring = ScoringRepo(s).get(alert.inspection_id)
        verdict = VerdictRepo(s).get(alert.verdict_id)

    if not all([brand, inspection, scoring, verdict]):
        missing = [
            name
            for name, val in [
                ("brand", brand),
                ("inspection", inspection),
                ("scoring", scoring),
                ("verdict", verdict),
            ]
            if val is None
        ]
        raise HTTPException(500, f"Alert references missing: {missing}")

    return {
        "alert": alert,
        "brand": brand,
        "inspection": inspection,
        "scoring": scoring,
        "verdict": verdict,
    }
