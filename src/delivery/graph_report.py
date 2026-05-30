"""v07 D8 — auto-report (CSV + PDF) generated from the W12 campaign graph.

Turns the threat-actor graph (src/graph/) into analyst/exec deliverables:
* a CSV export of campaigns, their domains, and shared infrastructure;
* a structured report payload (counts, top campaigns, IoC table);
* an optional PDF rendered via the existing ReportLab pipeline.

The CSV + structured payload are PURE and offline-testable. The PDF render is a
thin reuse of ReportLab and is exercised only when explicitly requested.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from ..graph.entity_model import Finding
from ..graph.campaign_detector import detect_campaigns, Campaign
from ..graph.edge_builder import build_graph


@dataclass
class GraphReport:
    total_findings: int
    total_campaigns: int
    total_nodes: int
    total_edges: int
    campaigns: list[Campaign]
    csv_text: str


def _campaigns_csv(campaigns: list[Campaign]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["campaign_id", "domain_count", "domains", "shared_infra", "finding_count"])
    for c in campaigns:
        w.writerow([
            c.campaign_id, len(c.domains), ";".join(c.domains),
            ";".join(c.shared_infra), c.finding_count,
        ])
    return buf.getvalue()


def build_graph_report(findings: list[Finding]) -> GraphReport:
    """Build the campaign report data (CSV + structured) from graph findings."""
    graph = build_graph(findings)
    campaigns = detect_campaigns(findings)
    return GraphReport(
        total_findings=len(findings),
        total_campaigns=len(campaigns),
        total_nodes=len(graph.nodes),
        total_edges=len(graph.edges),
        campaigns=campaigns,
        csv_text=_campaigns_csv(campaigns),
    )


def render_graph_report_pdf(report: GraphReport, out_path: str) -> str:
    """Render the report to a PDF via ReportLab. Returns the output path.

    Thin reuse of the existing PDF pipeline; only invoked on demand.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out_path, pagesize=A4)
    flow = [
        Paragraph("SpoofVane — Campaign Intelligence Report", styles["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(
            f"{report.total_campaigns} campaigns across {report.total_findings} findings "
            f"({report.total_nodes} entities, {report.total_edges} links).",
            styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]
    rows = [["Campaign", "#Domains", "Shared Infra", "#Findings"]]
    for c in report.campaigns:
        rows.append([c.campaign_id, str(len(c.domains)),
                     ", ".join(c.shared_infra) or "-", str(c.finding_count)])
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    flow.append(table)
    doc.build(flow)
    return out_path
