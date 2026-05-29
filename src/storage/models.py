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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
