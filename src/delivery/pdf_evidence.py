"""
Evidence-pack PDF builder.

Bundles the artefacts a registrar / hoster's abuse desk needs to action a
takedown into a single, self-contained PDF:

* Header — brand, suspect URL, verdict, severity, confidence
* Inspection metadata — ASN, registrar, registration date, country rendered from
* Similarity scoring breakdown
* Evidence bullets (Claude's reasoning) and the takedown draft
* Embedded screenshot of the suspect page
* DOM excerpt (first ~80 lines, escaped)
* Content-hash manifest — sha256 of every artefact, so the recipient can
  independently verify nothing was edited after the fact

We use ReportLab rather than WeasyPrint because it is pure-Python and needs no
native system libraries (Cairo / Pango), which matters for the demo
environment. The output is a single PDF written to ``settings.reports_dir``.
"""

from __future__ import annotations

import html
import io
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..common.logging import get_logger
from ..common.models import Alert, Brand, InspectionResult, ScoringResult, VerdictResult
from ..common.settings import get_settings
from ..storage.blob_store import blob_path, read_blob

logger = get_logger(__name__)


_SEVERITY_COLOR = {
    "critical": colors.HexColor("#b00020"),
    "high": colors.HexColor("#d84315"),
    "medium": colors.HexColor("#ef6c00"),
    "low": colors.HexColor("#2e7d32"),
}


def build_evidence_pdf(
    alert: Alert,
    brand: Brand,
    inspection: InspectionResult,
    scoring: ScoringResult,
    verdict: VerdictResult,
) -> Path:
    """Build the evidence PDF for ``alert`` and return its filesystem path.

    The output filename is deterministic per alert id, so calling this twice
    overwrites the previous file rather than accumulating duplicates.
    """
    settings = get_settings()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)

    out_path = settings.reports_dir / f"evidence_{alert.id}.pdf"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"SpoofVane Evidence Pack — {alert.id}",
        author="SpoofVane",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "h1",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1a237e"),
        spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#37474f"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=13,
        alignment=TA_LEFT,
    )
    mono = ParagraphStyle(
        "mono",
        parent=styles["Code"],
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#263238"),
    )

    story: list = []

    # --- Header --------------------------------------------------------------
    story.append(Paragraph("SpoofVane — Evidence Pack", h1))
    story.append(
        Paragraph(
            f"Alert <b>{html.escape(alert.id)}</b> generated "
            f"{alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            body,
        )
    )
    story.append(Spacer(1, 6))

    sev_color = _SEVERITY_COLOR.get(alert.severity.value, colors.black)
    summary_table = Table(
        [
            ["Brand", brand.name],
            ["Suspect URL", _wrap(alert.suspect_url)],
            ["Verdict", verdict.verdict.value.upper()],
            ["Severity", alert.severity.value.upper()],
            ["Confidence", f"{verdict.confidence:.0%}"],
            ["Suggested action", verdict.suggested_action],
            ["Composite score", f"{scoring.composite_score:.3f} (threshold {brand.score_threshold:.2f})"],
            ["Model", verdict.model_used],
        ],
        colWidths=[4 * cm, 12 * cm],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eceff1")),
                ("TEXTCOLOR", (1, 2), (1, 2), sev_color),
                ("TEXTCOLOR", (1, 3), (1, 3), sev_color),
                ("FONT", (1, 2), (1, 3), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8dc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(summary_table)

    # --- Inspection metadata -------------------------------------------------
    story.append(Paragraph("Inspection metadata", h2))
    insp_table = Table(
        [
            ["Inspection ID", inspection.id],
            ["Rendered from", inspection.rendered_country],
            ["Final URL", _wrap(inspection.final_url or "—")],
            ["HTTP status", str(inspection.http_status or "—")],
            ["ASN", inspection.asn or "—"],
            ["Registrar", inspection.registrar or "—"],
            [
                "Domain registered",
                (
                    inspection.registration_date.strftime("%Y-%m-%d")
                    if inspection.registration_date
                    else "—"
                ),
            ],
            ["Inspected at", inspection.inspected_at.strftime("%Y-%m-%d %H:%M:%S UTC")],
        ],
        colWidths=[4 * cm, 12 * cm],
    )
    insp_table.setStyle(_kv_style())
    story.append(insp_table)

    # --- Scoring breakdown ---------------------------------------------------
    story.append(Paragraph("Similarity scoring", h2))
    score_table = Table(
        [
            ["Signal", "Score", "Weight"],
            ["Perceptual hash (screenshot)", f"{scoring.phash_score:.3f}", "0.35"],
            ["DOM structural similarity", f"{scoring.dom_score:.3f}", "0.25"],
            ["Logo region similarity", f"{scoring.logo_score:.3f}", "0.30"],
            [
                "Favicon match",
                "yes" if scoring.favicon_match else "no",
                "0.10",
            ],
            ["Composite", f"{scoring.composite_score:.3f}", "—"],
        ],
        colWidths=[8 * cm, 4 * cm, 4 * cm],
    )
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8dc")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fff3e0")),
                ("FONT", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    story.append(score_table)

    # --- Detection signals (family + kit + cloaking) -----------------------
    has_signals = bool(
        verdict.attack_family
        or verdict.kit_match
        or verdict.cloaking_detected
    )
    if has_signals:
        story.append(Paragraph("Detection signals", h2))
        signal_rows = []
        if verdict.attack_family:
            signal_rows.append([
                "Attack family",
                verdict.attack_family.upper(),
                f"{(verdict.attack_family_confidence or 0):.0%} confidence",
            ])
        if verdict.kit_match:
            signal_rows.append([
                "Phishing kit",
                verdict.kit_match,
                f"{(verdict.kit_match_confidence or 0):.0%} confidence",
            ])
        if verdict.cloaking_detected:
            signal_rows.append([
                "Geo-cloaking",
                "DETECTED",
                "Cross-region renderer divergence",
            ])
        sig_table = Table(signal_rows, colWidths=[4 * cm, 6 * cm, 6 * cm])
        sig_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eceff1")),
                    ("FONT", (1, 0), (1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8dc")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(sig_table)
        if verdict.cloaking_evidence:
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Cloaking evidence:</b>", body))
            for line in verdict.cloaking_evidence:
                story.append(Paragraph(f"• {html.escape(line)}", body))

    # --- Evidence bullets ----------------------------------------------------
    story.append(Paragraph("Evidence (from AI verdict)", h2))
    if verdict.evidence_summary:
        for bullet in verdict.evidence_summary:
            story.append(Paragraph(f"• {html.escape(bullet)}", body))
    else:
        story.append(Paragraph("<i>No evidence bullets recorded.</i>", body))

    # --- Screenshot ----------------------------------------------------------
    screenshot_bytes = _try_read(inspection.screenshot_hash, ".png")
    if screenshot_bytes:
        story.append(PageBreak())
        story.append(Paragraph("Rendered screenshot of suspect page", h2))
        try:
            img = Image(io.BytesIO(screenshot_bytes), width=16 * cm, height=12 * cm)
            img.hAlign = "LEFT"
            story.append(img)
        except Exception as exc:  # noqa: BLE001
            logger.warning("evidence.screenshot_embed_failed", error=str(exc))
            story.append(Paragraph("<i>Screenshot could not be embedded.</i>", body))

    # --- DOM excerpt ---------------------------------------------------------
    dom_bytes = _try_read(inspection.dom_hash, ".html")
    if dom_bytes:
        story.append(PageBreak())
        story.append(Paragraph("DOM excerpt (first 80 lines)", h2))
        try:
            text = dom_bytes.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            text = ""
        excerpt = "\n".join(text.splitlines()[:80])
        story.append(Paragraph(_pre(excerpt), mono))

    # --- Takedown draft ------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("Takedown draft (for legal review)", h2))
    story.append(
        Paragraph(
            "<i>This draft has not been sent. Review and dispatch via your "
            "established takedown channel.</i>",
            body,
        )
    )
    story.append(Spacer(1, 4))
    story.append(Paragraph(_pre(verdict.takedown_draft), mono))

    # --- Hash manifest -------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("Content-hash manifest", h2))
    story.append(
        Paragraph(
            "Every artefact is stored content-addressed (SHA-256). Anyone with "
            "the bytes can recompute the hash and verify nothing was changed "
            "after detection. To verify: <tt>shasum -a 256 &lt;file&gt;</tt> "
            "and compare to the value below.",
            body,
        )
    )
    manifest_rows = [["Artefact", "SHA-256"]]
    if inspection.screenshot_hash:
        manifest_rows.append(["screenshot.png", inspection.screenshot_hash])
    if inspection.dom_hash:
        manifest_rows.append(["dom.html", inspection.dom_hash])
    if inspection.favicon_hash:
        manifest_rows.append(["favicon (md5)", inspection.favicon_hash])
    if brand.canonical_screenshot_hash:
        manifest_rows.append(["canonical_screenshot.png", brand.canonical_screenshot_hash])
    if brand.canonical_dom_hash:
        manifest_rows.append(["canonical_dom.html", brand.canonical_dom_hash])

    manifest_table = Table(manifest_rows, colWidths=[5 * cm, 11 * cm])
    manifest_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONT", (1, 1), (1, -1), "Courier"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8dc")),
            ]
        )
    )
    story.append(manifest_table)

    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            f"Generated by SpoofVane on "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            ParagraphStyle("footer", parent=body, fontSize=7, textColor=colors.grey),
        )
    )

    doc.build(story)
    logger.info(
        "evidence.pdf_built",
        alert_id=alert.id,
        path=str(out_path),
        size_bytes=out_path.stat().st_size,
    )
    return out_path


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _kv_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eceff1")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8dc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )


def _wrap(s: str, every: int = 80) -> str:
    """ReportLab does not wrap long unbroken strings (long URLs). Insert
    zero-width spaces every ``every`` characters so the layout breaks them."""
    if len(s) <= every:
        return html.escape(s)
    chunks = [s[i : i + every] for i in range(0, len(s), every)]
    return "&#8203;".join(html.escape(c) for c in chunks)


def _pre(s: str) -> str:
    """Escape and render as a soft-wrapped monospace block."""
    return html.escape(s).replace("\n", "<br/>").replace(" ", "&nbsp;")


def _try_read(sha256: str | None, suffix: str) -> bytes | None:
    if not sha256:
        return None
    path = blob_path(sha256, suffix)
    if not path.exists():
        return None
    try:
        return read_blob(sha256, suffix)
    except Exception as exc:  # noqa: BLE001
        logger.warning("evidence.blob_read_failed", sha256=sha256, error=str(exc))
        return None
