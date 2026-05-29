"""Type models shared across the discovery / inspection / scoring / verdict pipeline.

Pure data — no DB, no I/O. SQLAlchemy ORM models live in ``src.storage.models``
and are populated from these.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── Enums ─────────────────────────────────────────────────────────────


class Source(str, Enum):
    SERP = "serp"
    CERT_STREAM = "cert_stream"
    NEW_DOMAINS = "new_domains"
    MANUAL = "manual"
    PAID_AD = "paid_ad"
    MOBILE_APP_STORE = "mobile_app_store"
    GITHUB_LEAK = "github_leak"
    TELEGRAM_KIT = "telegram_kit"


class Verdict(str, Enum):
    PHISH = "phish"
    SUSPICIOUS = "suspicious"
    BENIGN = "benign"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertStatus(str, Enum):
    OPEN = "open"
    TRIAGED = "triaged"
    CONFIRMED = "confirmed"  # analyst marked as a real phishing site (true positive)
    DISMISSED = "dismissed"  # analyst marked as a false positive
    CLOSED = "closed"


# ─── Brand ─────────────────────────────────────────────────────────────


class Brand(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    login_url: HttpUrl
    payment_url: HttpUrl | None = None
    logo_path: Path | None = None
    target_country: str = "US"  # ISO 3166-1 alpha-2
    brand_keywords: list[str] = Field(default_factory=list)
    canonical_screenshot_hash: str | None = None
    canonical_dom_hash: str | None = None
    score_threshold: float = 0.65
    # Tenant scoping (v0.2)
    tenant_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


# ─── Discovery ─────────────────────────────────────────────────────────


class SuspectURL(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    url: str  # not HttpUrl — suspect URLs may be malformed
    source: Source
    discovered_at: datetime = Field(default_factory=_utcnow)
    discovery_metadata: dict = Field(default_factory=dict)


# ─── Inspection ────────────────────────────────────────────────────────


class InspectionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    suspect_url_id: str
    success: bool
    rendered_country: str
    final_url: str | None = None
    http_status: int | None = None

    # evidence pointers
    screenshot_path: Path | None = None
    screenshot_hash: str | None = None
    dom_path: Path | None = None
    dom_hash: str | None = None
    network_log_path: Path | None = None
    favicon_hash: str | None = None
    js_bundle_hashes: list[str] = Field(default_factory=list)

    # observed network metadata
    asn: str | None = None
    registrar: str | None = None
    registration_date: datetime | None = None

    inspected_at: datetime = Field(default_factory=_utcnow)
    error: str | None = None


# ─── Scoring ───────────────────────────────────────────────────────────


class ScoringResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inspection_id: str
    phash_score: float = Field(ge=0.0, le=1.0)
    dom_score: float = Field(ge=0.0, le=1.0)
    logo_score: float = Field(ge=0.0, le=1.0)
    favicon_match: bool
    composite_score: float = Field(ge=0.0, le=1.0)
    above_threshold: bool


# ─── Verdict ───────────────────────────────────────────────────────────


class VerdictResult(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    inspection_id: str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity
    evidence_summary: list[str]
    suggested_action: Literal["takedown", "watch", "dismiss"]
    takedown_draft: str
    model_used: str
    # Enhanced signals (v0.2)
    attack_family: str | None = None  # e.g. "m365", "banking", "crypto"
    attack_family_confidence: float | None = None
    kit_match: str | None = None  # e.g. "16Shop", "EvilProxy"
    kit_match_confidence: float | None = None
    cloaking_detected: bool = False
    cloaking_evidence: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


# ─── Alert ─────────────────────────────────────────────────────────────


class Alert(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    inspection_id: str
    verdict_id: str
    severity: Severity
    status: AlertStatus = AlertStatus.OPEN
    suspect_url: str
    triage_notes: str | None = None
    triaged_by: str | None = None
    triaged_at: datetime | None = None
    # Tenant scoping (v0.2)
    tenant_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
