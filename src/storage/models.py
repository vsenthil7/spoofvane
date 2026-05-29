"""SQLAlchemy ORM models.

These mirror the Pydantic models in src.common.models. Conversion in both
directions is done via the helpers at the bottom of this file.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── Brand ─────────────────────────────────────────────────────────────


class BrandRow(Base):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    login_url: Mapped[str] = mapped_column(String(500), nullable=False)
    payment_url: Mapped[str | None] = mapped_column(String(500))
    logo_path: Mapped[str | None] = mapped_column(String(500))
    target_country: Mapped[str] = mapped_column(String(2), default="US")
    brand_keywords: Mapped[list] = mapped_column(JSON, default=list)
    canonical_screenshot_hash: Mapped[str | None] = mapped_column(String(64))
    canonical_dom_hash: Mapped[str | None] = mapped_column(String(64))
    score_threshold: Mapped[float] = mapped_column(Float, default=0.65)
    # Tenant scoping (v0.2)
    tenant_id: Mapped[str | None] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ─── Tenants + API keys (v0.2) ────────────────────────────────────────


class TenantRow(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(String(40), default="trial")
    daily_spend_cap_usd: Mapped[float | None] = mapped_column(Float)
    daily_inspect_cap: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ApiKeyRow(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(40), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    secret_hash: Mapped[str] = mapped_column(String(64), index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ─── Cost-attribution events (v0.2) ───────────────────────────────────


class CostEventRow(Base):
    """One row per Bright Data API call we billed against."""

    __tablename__ = "cost_events"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(40), index=True)
    brand_id: Mapped[str | None] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(40))  # "serp", "unlocker", "browser_minute"
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    usd_amount: Mapped[float] = mapped_column(Float, default=0.0)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


# ─── Active-learning feedback (v0.2) ──────────────────────────────────


class FeedbackEventRow(Base):
    """Captured analyst triage outcomes — feeds back into scoring weights."""

    __tablename__ = "feedback_events"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(40), ForeignKey("alerts.id"), index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(40), index=True)
    brand_id: Mapped[str | None] = mapped_column(String(40), index=True)
    # outcome ∈ {true_positive, false_positive, indeterminate}
    outcome: Mapped[str] = mapped_column(String(40), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    # Snapshot of which signals were present, so we can correlate later
    attack_family: Mapped[str | None] = mapped_column(String(40))
    kit_match: Mapped[str | None] = mapped_column(String(80))
    cloaking_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    composite_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ─── Audit log (v0.2) ─────────────────────────────────────────────────


class AuditLogRow(Base):
    """Append-only record of every state-changing operation."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(40), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(80), index=True)
    target_kind: Mapped[str | None] = mapped_column(String(40))
    target_id: Mapped[str | None] = mapped_column(String(40))
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    request_ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    # Outcome / extra detail
    status_code: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)
    # Tamper-evident hash chain (each row hashes the previous row_hash)
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    row_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


class AlertNoteRow(Base):
    """Append-only analyst notes on an alert — a collaboration thread.

    Distinct from ``alerts.triage_notes`` (a single overwriteable field):
    this preserves every analyst comment with author + timestamp so an
    investigation has a full audit trail of who-said-what-when.
    """

    __tablename__ = "alert_notes"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(40), ForeignKey("alerts.id"), index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(40), index=True)
    author: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


# ─── Suspect URL ───────────────────────────────────────────────────────


class SuspectURLRow(Base):
    __tablename__ = "suspect_urls"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(40), ForeignKey("brands.id"), index=True)
    url: Mapped[str] = mapped_column(String(2000), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    discovery_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


# ─── Inspection ────────────────────────────────────────────────────────


class InspectionRow(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    suspect_url_id: Mapped[str] = mapped_column(String(40), ForeignKey("suspect_urls.id"), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    rendered_country: Mapped[str] = mapped_column(String(2), default="US")
    final_url: Mapped[str | None] = mapped_column(String(2000))
    http_status: Mapped[int | None] = mapped_column(Integer)

    screenshot_path: Mapped[str | None] = mapped_column(String(500))
    screenshot_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    dom_path: Mapped[str | None] = mapped_column(String(500))
    dom_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    network_log_path: Mapped[str | None] = mapped_column(String(500))
    favicon_hash: Mapped[str | None] = mapped_column(String(64))
    js_bundle_hashes: Mapped[list] = mapped_column(JSON, default=list)

    asn: Mapped[str | None] = mapped_column(String(40))
    registrar: Mapped[str | None] = mapped_column(String(200))
    registration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    error: Mapped[str | None] = mapped_column(Text)

    # tamper-evidence chain
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    row_hash: Mapped[str | None] = mapped_column(String(64))


# ─── Scoring ───────────────────────────────────────────────────────────


class ScoringRow(Base):
    __tablename__ = "scoring_results"

    inspection_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("inspections.id"), primary_key=True
    )
    phash_score: Mapped[float] = mapped_column(Float)
    dom_score: Mapped[float] = mapped_column(Float)
    logo_score: Mapped[float] = mapped_column(Float)
    favicon_match: Mapped[bool] = mapped_column(Boolean)
    composite_score: Mapped[float] = mapped_column(Float)
    above_threshold: Mapped[bool] = mapped_column(Boolean)


# ─── Verdict ───────────────────────────────────────────────────────────


class VerdictRow(Base):
    __tablename__ = "verdicts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    inspection_id: Mapped[str] = mapped_column(String(40), ForeignKey("inspections.id"), index=True)
    verdict: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(20))
    evidence_summary: Mapped[list] = mapped_column(JSON)
    suggested_action: Mapped[str] = mapped_column(String(20))
    takedown_draft: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String(80))
    # Enhanced signals (v0.2)
    attack_family: Mapped[str | None] = mapped_column(String(40), index=True)
    attack_family_confidence: Mapped[float | None] = mapped_column(Float)
    kit_match: Mapped[str | None] = mapped_column(String(80), index=True)
    kit_match_confidence: Mapped[float | None] = mapped_column(Float)
    cloaking_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    cloaking_evidence: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ─── Alert ─────────────────────────────────────────────────────────────


class AlertRow(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(40), ForeignKey("brands.id"), index=True)
    inspection_id: Mapped[str] = mapped_column(String(40), ForeignKey("inspections.id"))
    verdict_id: Mapped[str] = mapped_column(String(40), ForeignKey("verdicts.id"))
    severity: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    suspect_url: Mapped[str] = mapped_column(String(2000))
    triage_notes: Mapped[str | None] = mapped_column(Text)
    triaged_by: Mapped[str | None] = mapped_column(String(200))
    triaged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Tenant scoping (v0.2)
    tenant_id: Mapped[str | None] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
