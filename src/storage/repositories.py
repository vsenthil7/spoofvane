"""Data-access repositories for the ORM tables.

Each repository converts between Pydantic types (``src.common.models``) and
the SQLAlchemy ORM rows (``src.storage.models``). The rest of the app should
go through these — no direct ORM access elsewhere.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..common import models as m
from . import models as orm


# ─── helpers ───────────────────────────────────────────────────────────


def _to_utc(dt: datetime | None) -> datetime | None:
    """Treat naive datetimes from SQLite as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ─── BrandRepo ─────────────────────────────────────────────────────────


class BrandRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def create(self, brand: m.Brand) -> m.Brand:
        row = orm.BrandRow(
            id=brand.id,
            name=brand.name,
            login_url=str(brand.login_url),
            payment_url=str(brand.payment_url) if brand.payment_url else None,
            logo_path=str(brand.logo_path) if brand.logo_path else None,
            target_country=brand.target_country,
            brand_keywords=brand.brand_keywords,
            canonical_screenshot_hash=brand.canonical_screenshot_hash,
            canonical_dom_hash=brand.canonical_dom_hash,
            score_threshold=brand.score_threshold,
            created_at=brand.created_at,
        )
        self.s.add(row)
        self.s.flush()
        return self._to_pydantic(row)

    def get(self, brand_id: str) -> m.Brand | None:
        row = self.s.get(orm.BrandRow, brand_id)
        return self._to_pydantic(row) if row else None

    def get_by_name(self, name: str) -> m.Brand | None:
        row = self.s.scalar(select(orm.BrandRow).where(orm.BrandRow.name == name))
        return self._to_pydantic(row) if row else None

    def list_all(self) -> list[m.Brand]:
        rows = self.s.scalars(select(orm.BrandRow).order_by(orm.BrandRow.created_at)).all()
        return [self._to_pydantic(r) for r in rows]

    @staticmethod
    def _to_pydantic(row: orm.BrandRow) -> m.Brand:
        return m.Brand(
            id=row.id,
            name=row.name,
            login_url=row.login_url,
            payment_url=row.payment_url,
            logo_path=row.logo_path,
            target_country=row.target_country,
            brand_keywords=row.brand_keywords or [],
            canonical_screenshot_hash=row.canonical_screenshot_hash,
            canonical_dom_hash=row.canonical_dom_hash,
            score_threshold=row.score_threshold,
            created_at=_to_utc(row.created_at),
        )


# ─── SuspectURLRepo ────────────────────────────────────────────────────


class SuspectURLRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def create(self, susp: m.SuspectURL) -> m.SuspectURL:
        row = orm.SuspectURLRow(
            id=susp.id,
            brand_id=susp.brand_id,
            url=susp.url,
            source=susp.source.value,
            discovered_at=susp.discovered_at,
            discovery_metadata=susp.discovery_metadata,
        )
        self.s.add(row)
        self.s.flush()
        return self._to_pydantic(row)

    def list_for_brand(self, brand_id: str, limit: int = 100) -> list[m.SuspectURL]:
        rows = self.s.scalars(
            select(orm.SuspectURLRow)
            .where(orm.SuspectURLRow.brand_id == brand_id)
            .order_by(desc(orm.SuspectURLRow.discovered_at))
            .limit(limit)
        ).all()
        return [self._to_pydantic(r) for r in rows]

    def count_for_brand(self, brand_id: str) -> int:
        return self.s.scalar(
            select(orm.SuspectURLRow).where(orm.SuspectURLRow.brand_id == brand_id).with_only_columns(orm.SuspectURLRow.id).order_by(None)
        ) and self.s.query(orm.SuspectURLRow).filter(orm.SuspectURLRow.brand_id == brand_id).count() or 0

    @staticmethod
    def _to_pydantic(row: orm.SuspectURLRow) -> m.SuspectURL:
        return m.SuspectURL(
            id=row.id,
            brand_id=row.brand_id,
            url=row.url,
            source=m.Source(row.source),
            discovered_at=_to_utc(row.discovered_at),
            discovery_metadata=row.discovery_metadata or {},
        )


# ─── InspectionRepo (with hash chain) ──────────────────────────────────


class InspectionRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def create(self, inspection: m.InspectionResult) -> m.InspectionResult:
        # Hash chain: row_hash = sha256(prev_hash || canonical_json)
        last = self.s.scalar(
            select(orm.InspectionRow).order_by(desc(orm.InspectionRow.inspected_at)).limit(1)
        )
        prev_hash = last.row_hash if last else "0" * 64

        canonical = json.dumps(
            {
                "id": inspection.id,
                "suspect_url_id": inspection.suspect_url_id,
                "success": inspection.success,
                "screenshot_hash": inspection.screenshot_hash,
                "dom_hash": inspection.dom_hash,
                "inspected_at": inspection.inspected_at.isoformat(),
            },
            sort_keys=True,
        )
        row_hash = hashlib.sha256((prev_hash + canonical).encode()).hexdigest()

        row = orm.InspectionRow(
            id=inspection.id,
            suspect_url_id=inspection.suspect_url_id,
            success=inspection.success,
            rendered_country=inspection.rendered_country,
            final_url=inspection.final_url,
            http_status=inspection.http_status,
            screenshot_path=str(inspection.screenshot_path) if inspection.screenshot_path else None,
            screenshot_hash=inspection.screenshot_hash,
            dom_path=str(inspection.dom_path) if inspection.dom_path else None,
            dom_hash=inspection.dom_hash,
            network_log_path=str(inspection.network_log_path) if inspection.network_log_path else None,
            favicon_hash=inspection.favicon_hash,
            js_bundle_hashes=inspection.js_bundle_hashes,
            asn=inspection.asn,
            registrar=inspection.registrar,
            registration_date=inspection.registration_date,
            inspected_at=inspection.inspected_at,
            error=inspection.error,
            prev_hash=prev_hash,
            row_hash=row_hash,
        )
        self.s.add(row)
        self.s.flush()
        return self._to_pydantic(row)

    def get(self, inspection_id: str) -> m.InspectionResult | None:
        row = self.s.get(orm.InspectionRow, inspection_id)
        return self._to_pydantic(row) if row else None

    @staticmethod
    def _to_pydantic(row: orm.InspectionRow) -> m.InspectionResult:
        from pathlib import Path

        return m.InspectionResult(
            id=row.id,
            suspect_url_id=row.suspect_url_id,
            success=row.success,
            rendered_country=row.rendered_country,
            final_url=row.final_url,
            http_status=row.http_status,
            screenshot_path=Path(row.screenshot_path) if row.screenshot_path else None,
            screenshot_hash=row.screenshot_hash,
            dom_path=Path(row.dom_path) if row.dom_path else None,
            dom_hash=row.dom_hash,
            network_log_path=Path(row.network_log_path) if row.network_log_path else None,
            favicon_hash=row.favicon_hash,
            js_bundle_hashes=row.js_bundle_hashes or [],
            asn=row.asn,
            registrar=row.registrar,
            registration_date=_to_utc(row.registration_date),
            inspected_at=_to_utc(row.inspected_at),
            error=row.error,
        )


# ─── ScoringRepo ───────────────────────────────────────────────────────


class ScoringRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def create(self, scoring: m.ScoringResult) -> m.ScoringResult:
        row = orm.ScoringRow(
            inspection_id=scoring.inspection_id,
            phash_score=scoring.phash_score,
            dom_score=scoring.dom_score,
            logo_score=scoring.logo_score,
            favicon_match=scoring.favicon_match,
            composite_score=scoring.composite_score,
            above_threshold=scoring.above_threshold,
        )
        self.s.add(row)
        self.s.flush()
        return scoring

    def get(self, inspection_id: str) -> m.ScoringResult | None:
        row = self.s.get(orm.ScoringRow, inspection_id)
        if not row:
            return None
        return m.ScoringResult(
            inspection_id=row.inspection_id,
            phash_score=row.phash_score,
            dom_score=row.dom_score,
            logo_score=row.logo_score,
            favicon_match=row.favicon_match,
            composite_score=row.composite_score,
            above_threshold=row.above_threshold,
        )


# ─── VerdictRepo ───────────────────────────────────────────────────────


class VerdictRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def create(self, verdict: m.VerdictResult) -> m.VerdictResult:
        row = orm.VerdictRow(
            id=verdict.id,
            inspection_id=verdict.inspection_id,
            verdict=verdict.verdict.value,
            confidence=verdict.confidence,
            severity=verdict.severity.value,
            evidence_summary=verdict.evidence_summary,
            suggested_action=verdict.suggested_action,
            takedown_draft=verdict.takedown_draft,
            model_used=verdict.model_used,
            created_at=verdict.created_at,
        )
        self.s.add(row)
        self.s.flush()
        return verdict

    def get(self, verdict_id: str) -> m.VerdictResult | None:
        row = self.s.get(orm.VerdictRow, verdict_id)
        if not row:
            return None
        return m.VerdictResult(
            id=row.id,
            inspection_id=row.inspection_id,
            verdict=m.Verdict(row.verdict),
            confidence=row.confidence,
            severity=m.Severity(row.severity),
            evidence_summary=row.evidence_summary,
            suggested_action=row.suggested_action,
            takedown_draft=row.takedown_draft,
            model_used=row.model_used,
            created_at=_to_utc(row.created_at),
        )


# ─── AlertRepo ─────────────────────────────────────────────────────────


class AlertRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    def create(self, alert: m.Alert) -> m.Alert:
        row = orm.AlertRow(
            id=alert.id,
            brand_id=alert.brand_id,
            inspection_id=alert.inspection_id,
            verdict_id=alert.verdict_id,
            severity=alert.severity.value,
            status=alert.status.value,
            suspect_url=alert.suspect_url,
            triage_notes=alert.triage_notes,
            triaged_by=alert.triaged_by,
            triaged_at=alert.triaged_at,
            created_at=alert.created_at,
        )
        self.s.add(row)
        self.s.flush()
        return alert

    def get(self, alert_id: str) -> m.Alert | None:
        row = self.s.get(orm.AlertRow, alert_id)
        return self._to_pydantic(row) if row else None

    def list_for_brand(
        self,
        brand_id: str | None = None,
        status: m.AlertStatus | None = None,
        severity: m.Severity | None = None,
        limit: int = 50,
    ) -> list[m.Alert]:
        q = select(orm.AlertRow).order_by(desc(orm.AlertRow.created_at)).limit(limit)
        if brand_id:
            q = q.where(orm.AlertRow.brand_id == brand_id)
        if status:
            q = q.where(orm.AlertRow.status == status.value)
        if severity:
            q = q.where(orm.AlertRow.severity == severity.value)
        rows = self.s.scalars(q).all()
        return [self._to_pydantic(r) for r in rows]

    def update_triage(
        self,
        alert_id: str,
        status: m.AlertStatus,
        notes: str | None = None,
        actor: str | None = None,
    ) -> m.Alert | None:
        row = self.s.get(orm.AlertRow, alert_id)
        if not row:
            return None
        row.status = status.value
        row.triage_notes = notes
        row.triaged_by = actor
        row.triaged_at = datetime.now(timezone.utc)
        self.s.flush()
        return self._to_pydantic(row)

    @staticmethod
    def _to_pydantic(row: orm.AlertRow) -> m.Alert:
        return m.Alert(
            id=row.id,
            brand_id=row.brand_id,
            inspection_id=row.inspection_id,
            verdict_id=row.verdict_id,
            severity=m.Severity(row.severity),
            status=m.AlertStatus(row.status),
            suspect_url=row.suspect_url,
            triage_notes=row.triage_notes,
            triaged_by=row.triaged_by,
            triaged_at=_to_utc(row.triaged_at),
            created_at=_to_utc(row.created_at),
        )
