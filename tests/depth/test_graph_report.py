"""v07 D8 Gate — auto-report from the campaign graph differential probe.

The report aggregates the W12 graph into campaigns; a shared-cert+kit cluster
shows as ONE campaign row in the CSV with the shared infra listed; distinct
finding sets yield distinct reports; the CSV parses with the expected header;
the PDF renders to a real non-empty file.
"""
from __future__ import annotations

import csv
import io
import os

from src.graph.entity_model import Finding
from src.delivery.graph_report import build_graph_report, render_graph_report_pdf

SHARED_CERT = "sha256:abc123"
FINDINGS = [
    Finding("f1", domain="acme-login.top", cert_sha=SHARED_CERT, kit_family="m365",
            registrar="Namecheap", surface="domain"),
    Finding("f2", domain="acme-verify.xyz", cert_sha=SHARED_CERT, kit_family="m365",
            registrar="Namecheap", surface="domain"),
    Finding("f3", domain="unrelated.com", cert_sha="sha256:zzz", kit_family="banking",
            surface="domain"),
]


def test_report_aggregates_campaigns():
    rep = build_graph_report(FINDINGS)
    assert rep.total_findings == 3
    assert rep.total_campaigns >= 2          # acme cluster + unrelated
    assert rep.total_nodes > 0 and rep.total_edges > 0


def test_csv_has_header_and_collapses_shared_cluster():
    rep = build_graph_report(FINDINGS)
    rows = list(csv.reader(io.StringIO(rep.csv_text)))
    assert rows[0] == ["campaign_id", "domain_count", "domains", "shared_infra",
                       "finding_count"]
    # Find the campaign row containing the two acme domains.
    acme_row = next(r for r in rows[1:] if "acme-login.top" in r[2])
    assert "acme-verify.xyz" in acme_row[2]      # collapsed into one campaign
    assert "unrelated.com" not in acme_row[2]
    assert int(acme_row[1]) == 2                  # domain_count


def test_distinct_findings_distinct_reports():
    a = build_graph_report(FINDINGS)
    b = build_graph_report([Finding("g1", domain="other.com", cert_sha="sha256:q")])
    assert a.csv_text != b.csv_text
    assert a.total_findings != b.total_findings


def test_empty_report():
    rep = build_graph_report([])
    assert rep.total_findings == 0
    assert rep.total_campaigns == 0
    rows = list(csv.reader(io.StringIO(rep.csv_text)))
    assert rows[0][0] == "campaign_id"   # header still present
    assert len(rows) == 1                # header only


def test_pdf_renders_nonempty(tmp_path):
    rep = build_graph_report(FINDINGS)
    out = str(tmp_path / "campaign_report.pdf")
    path = render_graph_report_pdf(rep, out)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 500   # a real PDF, not an empty stub
    with open(path, "rb") as fh:
        assert fh.read(5) == b"%PDF-"     # valid PDF magic bytes
