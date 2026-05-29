"""
DoppelDomain HTTP API + triage dashboard.

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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, HttpUrl

from ..common.ids import brand_id as gen_brand_id
from ..common.logging import get_logger
from ..common.models import Alert, AlertStatus, Brand, SuspectURL, Verdict
from ..common.pipeline import PipelineStats, run_pipeline_for_brand
from ..common.settings import get_settings
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


# --------------------------------------------------------------------------- #
# App + templates
# --------------------------------------------------------------------------- #

app = FastAPI(
    title="DoppelDomain",
    version="0.1.0",
    description=(
        "Brand-impersonation detection — Bright Data Hackathon Track 3. "
        "Catches phishing infrastructure by fingerprinting the rendered page, "
        "not just the domain name."
    ),
)

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


# --------------------------------------------------------------------------- #
# Brands
# --------------------------------------------------------------------------- #


@app.post("/api/brands", tags=["brands"], status_code=201)
def create_brand(payload: BrandCreate) -> dict:
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
    )
    with session_scope() as s:
        repo = BrandRepo(s)
        if repo.get_by_name(brand.name) is not None:
            raise HTTPException(409, f"Brand already exists: {brand.name}")
        brand = repo.create(brand)
    return brand.model_dump(mode="json")


@app.get("/api/brands", tags=["brands"])
def list_brands() -> list[dict]:
    with session_scope() as s:
        brands = BrandRepo(s).list_all()
    return [b.model_dump(mode="json") for b in brands]


@app.get("/api/brands/{brand_id}", tags=["brands"])
def get_brand(brand_id: Annotated[str, PathParam(min_length=1)]) -> dict:
    with session_scope() as s:
        brand = BrandRepo(s).get(brand_id)
    if brand is None:
        raise HTTPException(404, f"Brand not found: {brand_id}")
    return brand.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# Discovery + pipeline
# --------------------------------------------------------------------------- #


@app.post("/api/discovery/run", tags=["pipeline"])
def run_discovery(
    payload: DiscoveryRunRequest,
    background: BackgroundTasks,
    wait: bool = Query(default=False, description="Block until pipeline completes"),
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


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #


@app.get("/api/alerts", tags=["alerts"])
def list_alerts(
    brand_id: str | None = Query(default=None),
    status: AlertStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    with session_scope() as s:
        repo = AlertRepo(s)
        if brand_id:
            alerts = repo.list_for_brand(brand_id, status=status, limit=limit)
        else:
            alerts = repo.list_for_brand(brand_id=None, status=status, limit=limit)
    return [a.model_dump(mode="json") for a in alerts]


@app.get("/api/alerts/{alert_id}", tags=["alerts"])
def get_alert(alert_id: str) -> dict:
    bundle = _load_alert_bundle(alert_id)
    return {
        "alert": bundle["alert"].model_dump(mode="json"),
        "brand": bundle["brand"].model_dump(mode="json"),
        "inspection": bundle["inspection"].model_dump(mode="json"),
        "scoring": bundle["scoring"].model_dump(mode="json"),
        "verdict": bundle["verdict"].model_dump(mode="json"),
    }


@app.post("/api/alerts/{alert_id}/triage", tags=["alerts"])
def triage_alert(alert_id: str, payload: TriageRequest) -> dict:
    with session_scope() as s:
        repo = AlertRepo(s)
        existing = repo.get(alert_id)
        if existing is None:
            raise HTTPException(404, f"Alert not found: {alert_id}")
        updated = repo.update_triage(
            alert_id,
            status=payload.status,
            notes=payload.notes,
            actor=payload.triaged_by,
        )
    return updated.model_dump(mode="json")


@app.get(
    "/api/alerts/{alert_id}/evidence.pdf",
    tags=["alerts"],
    response_class=FileResponse,
)
def evidence_pdf(alert_id: str) -> FileResponse:
    bundle = _load_alert_bundle(alert_id)
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


@app.get("/", response_class=HTMLResponse, tags=["dashboard"])
def dashboard(request: Request) -> HTMLResponse:
    with session_scope() as s:
        brands = BrandRepo(s).list_all()
        all_alerts: list[Alert] = []
        for b in brands:
            all_alerts.extend(AlertRepo(s).list_for_brand(b.id, limit=100))
    all_alerts.sort(key=lambda a: a.created_at, reverse=True)

    brand_lookup = {b.id: b for b in brands}
    summary = {
        "total_alerts": len(all_alerts),
        "open": sum(1 for a in all_alerts if a.status == AlertStatus.OPEN),
        "critical": sum(1 for a in all_alerts if a.severity.value == "critical"),
        "high": sum(1 for a in all_alerts if a.severity.value == "high"),
    }
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "brands": brands,
            "brands_json": [b.model_dump(mode="json") for b in brands],
            "alerts": all_alerts,
            "brand_lookup": brand_lookup,
            "summary": summary,
            "mock_mode": settings.mock_mode,
        },
    )


@app.get("/alerts/{alert_id}", response_class=HTMLResponse, tags=["dashboard"])
def alert_detail(request: Request, alert_id: str) -> HTMLResponse:
    bundle = _load_alert_bundle(alert_id)
    return templates.TemplateResponse(
        request,
        "alert_detail.html",
        {
            "alert": bundle["alert"],
            "brand": bundle["brand"],
            "inspection": bundle["inspection"],
            "scoring": bundle["scoring"],
            "verdict": bundle["verdict"],
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
