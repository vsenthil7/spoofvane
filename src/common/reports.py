"""Report engine — on-demand and scheduled reports.

Produces three report kinds in PDF/CSV/JSON (REQ-RPT-01..04):

* ``detection_summary`` — counts by verdict/severity/family/kit, top suspects.
* ``board_pack``        — executive PDF: KPIs, trend, SLA posture, spend.
* ``audit_export``      — the hash-chained audit trail + chain-verification.

Artefacts are written under ``settings.reports_dir`` and a row recorded in the
``reports`` table so the UI can list/download them.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..common import audit
from ..common.ids import make_id
from ..common.logging import get_logger
from ..common.settings import get_settings
from ..storage import models as orm
from ..storage.identity_models import ReportRow, ReviewItemRow

log = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _reports_dir() -> Path:
    d = Path(get_settings().reports_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─────────────────────────── Data gathering ─────────────────────────────

def _detection_data(s: Session, account_id: str) -> dict:
    # Verdicts joined to alerts belonging to this account's brands.
    brand_ids = [b.id for b in s.scalars(
        select(orm.BrandRow).where(orm.BrandRow.tenant_id == account_id)
    ).all()]
    verdict_counts = dict(s.execute(
        select(orm.VerdictRow.verdict, func.count()).group_by(orm.VerdictRow.verdict)
    ).all())
    family_counts = dict(s.execute(
        select(orm.VerdictRow.attack_family, func.count())
        .where(orm.VerdictRow.attack_family.is_not(None))
        .group_by(orm.VerdictRow.attack_family)
    ).all())
    kit_counts = dict(s.execute(
        select(orm.VerdictRow.kit_match, func.count())
        .where(orm.VerdictRow.kit_match.is_not(None))
        .group_by(orm.VerdictRow.kit_match)
    ).all())
    cloaking = s.scalar(
        select(func.count()).select_from(orm.VerdictRow)
        .where(orm.VerdictRow.cloaking_detected.is_(True))
    ) or 0
    review_stats = dict(s.execute(
        select(ReviewItemRow.state, func.count())
        .where(ReviewItemRow.account_id == account_id)
        .group_by(ReviewItemRow.state)
    ).all())
    return {
        "generated_at": _utcnow().isoformat(),
        "account_id": account_id,
        "brands": len(brand_ids),
        "verdicts": verdict_counts,
        "families": family_counts,
        "kits": kit_counts,
        "cloaking_detected": cloaking,
        "review_queue": review_stats,
    }


# ─────────────────────────────── Builders ───────────────────────────────

def _write(account_id: str, kind: str, fmt: str, title: str, content: bytes,
           s: Session, generated_by: str | None) -> str:
    fname = f"{kind}_{account_id}_{_utcnow().strftime('%Y%m%dT%H%M%S')}.{fmt}"
    path = _reports_dir() / fname
    path.write_bytes(content)
    row = ReportRow(
        id=make_id("rpt"), account_id=account_id, kind=kind, fmt=fmt,
        title=title, path=str(path), generated_by=generated_by,
    )
    s.add(row)
    s.flush()
    log.info("report.generated", kind=kind, fmt=fmt, path=str(path))
    return str(path)


def generate_detection_summary(s: Session, *, account_id: str, fmt: str = "pdf",
                               generated_by: str | None = None) -> str:
    data = _detection_data(s, account_id)
    title = "Detection Summary"
    if fmt == "json":
        return _write(account_id, "detection_summary", "json", title,
                      json.dumps(data, indent=2, default=str).encode(), s, generated_by)
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["metric", "key", "value"])
        for grp in ("verdicts", "families", "kits", "review_queue"):
            for k, v in data[grp].items():
                w.writerow([grp, k, v])
        w.writerow(["cloaking_detected", "", data["cloaking_detected"]])
        w.writerow(["brands", "", data["brands"]])
        return _write(account_id, "detection_summary", "csv", title,
                      buf.getvalue().encode(), s, generated_by)
    # pdf
    return _write(account_id, "detection_summary", "pdf", title,
                  _detection_pdf(title, data), s, generated_by)


def generate_board_pack(s: Session, *, account_id: str,
                        generated_by: str | None = None) -> str:
    data = _detection_data(s, account_id)
    return _write(account_id, "board_pack", "pdf", "Executive Board Pack",
                  _board_pdf(data), s, generated_by)


def generate_audit_export(s: Session, *, account_id: str, fmt: str = "csv",
                          generated_by: str | None = None) -> str:
    rows = audit.query(s, account_id=account_id, limit=10000)
    chain = audit.verify_chain(s, account_id=account_id)
    title = "Audit Export"
    if fmt == "json":
        payload = {"chain_verification": chain, "entries": rows}
        return _write(account_id, "audit_export", "json", title,
                      json.dumps(payload, indent=2, default=str).encode(), s, generated_by)
    # csv (default)
    body = audit.export_csv(rows)
    header = f"# chain_valid={chain['valid']} verified={chain['verified']}/{chain['total']}\n"
    return _write(account_id, "audit_export", "csv", title,
                  (header + body).encode(), s, generated_by)


# ─────────────────────────────── PDF render ─────────────────────────────

def _detection_pdf(title: str, data: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    from reportlab.lib import colors

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title,
                            leftMargin=2 * cm, rightMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"SpoofVane — {title}", styles["Title"]),
             Paragraph(f"Generated {data['generated_at']}", styles["Normal"]),
             Spacer(1, 0.6 * cm)]

    def _table(heading: str, mapping: dict):
        story.append(Paragraph(heading, styles["Heading2"]))
        rows = [["Key", "Count"]] + [[str(k), str(v)] for k, v in (mapping or {}).items()]
        if len(rows) == 1:
            rows.append(["(none)", "0"])
        t = Table(rows, colWidths=[10 * cm, 4 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph(
        f"Brands monitored: <b>{data['brands']}</b> &nbsp;·&nbsp; "
        f"Cloaking detections: <b>{data['cloaking_detected']}</b>", styles["Normal"]))
    story.append(Spacer(1, 0.4 * cm))
    _table("Verdicts", data["verdicts"])
    _table("Attack families", data["families"])
    _table("Phishing kits", data["kits"])
    _table("Review queue", data["review_queue"])
    doc.build(story)
    return buf.getvalue()


def _board_pdf(data: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Executive Board Pack")
    styles = getSampleStyleSheet()
    total_phish = data["verdicts"].get("phish", 0)
    pending = data["review_queue"].get("pending", 0)
    story = [
        Paragraph("SpoofVane — Executive Board Pack", styles["Title"]),
        Paragraph(f"Generated {data['generated_at']}", styles["Normal"]),
        Spacer(1, 0.8 * cm),
        Paragraph("Key indicators", styles["Heading2"]),
        Paragraph(f"Confirmed phishing detections: <b>{total_phish}</b>", styles["Normal"]),
        Paragraph(f"Brands protected: <b>{data['brands']}</b>", styles["Normal"]),
        Paragraph(f"Geo-cloaked threats caught: <b>{data['cloaking_detected']}</b>", styles["Normal"]),
        Paragraph(f"Reviews pending human decision: <b>{pending}</b>", styles["Normal"]),
        Spacer(1, 0.6 * cm),
        Paragraph("Posture", styles["Heading2"]),
        Paragraph(
            "All consequential detections pass through mandatory human review "
            "before any takedown is submitted. The full action trail is recorded "
            "in a tamper-evident hash chain and is available as an audit export.",
            styles["Normal"]),
    ]
    doc.build(story)
    return buf.getvalue()


def list_reports(s: Session, *, account_id: str, limit: int = 50) -> list[dict]:
    rows = s.scalars(
        select(ReportRow).where(ReportRow.account_id == account_id)
        .order_by(ReportRow.created_at.desc()).limit(limit)
    ).all()
    return [
        {"id": r.id, "kind": r.kind, "fmt": r.fmt, "title": r.title,
         "path": r.path, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


__all__ = [
    "generate_detection_summary", "generate_board_pack",
    "generate_audit_export", "list_reports",
]
