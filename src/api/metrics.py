"""
Prometheus metrics exposition.

Exposes operational metrics in the Prometheus text format at ``/metrics``.
We hand-roll the exposition rather than pull in ``prometheus_client`` because
the metrics we care about are all derivable from current DB state — counts of
alerts by severity/status, discovered suspects by source, Bright Data spend by
kind, feedback events by outcome. A scrape computes them fresh.

For counters that genuinely need in-process accumulation (request counts,
pipeline durations) a real deployment would add ``prometheus_client`` with
proper Counter/Histogram objects. This module covers the gauge-style metrics
that matter for a hackathon demo and for basic alerting (e.g. "page me if
open critical alerts > N").

Metric naming follows Prometheus conventions: ``spoofvane_<subsystem>_<unit>``.
"""

from __future__ import annotations

from sqlalchemy import func, select

from ..common.logging import get_logger
from ..storage import models as orm
from ..storage.db import session_scope

logger = get_logger(__name__)


def render_metrics() -> str:
    """Return the full Prometheus exposition text for a scrape."""
    lines: list[str] = []

    def _emit(name: str, help_text: str, metric_type: str, samples: list[tuple[dict, float]]) -> None:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {metric_type}")
        for labels, value in samples:
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                lines.append(f"{name}{{{label_str}}} {value}")
            else:
                lines.append(f"{name} {value}")

    with session_scope() as s:
        # Alerts by severity
        sev_rows = s.execute(
            select(orm.AlertRow.severity, func.count()).group_by(orm.AlertRow.severity)
        ).all()
        _emit(
            "spoofvane_alerts_total",
            "Total alerts by severity",
            "gauge",
            [({"severity": sev}, float(cnt)) for sev, cnt in sev_rows],
        )

        # Alerts by status
        status_rows = s.execute(
            select(orm.AlertRow.status, func.count()).group_by(orm.AlertRow.status)
        ).all()
        _emit(
            "spoofvane_alerts_by_status",
            "Total alerts by triage status",
            "gauge",
            [({"status": st}, float(cnt)) for st, cnt in status_rows],
        )

        # Verdicts with cloaking detected
        cloaking_count = s.scalar(
            select(func.count()).where(orm.VerdictRow.cloaking_detected.is_(True))
        ) or 0
        _emit(
            "spoofvane_cloaking_detected_total",
            "Verdicts where geo-cloaking was detected",
            "gauge",
            [({}, float(cloaking_count))],
        )

        # Verdicts by attack family
        family_rows = s.execute(
            select(orm.VerdictRow.attack_family, func.count())
            .where(orm.VerdictRow.attack_family.is_not(None))
            .group_by(orm.VerdictRow.attack_family)
        ).all()
        _emit(
            "spoofvane_verdicts_by_family",
            "Verdicts by detected attack family",
            "gauge",
            [({"family": fam}, float(cnt)) for fam, cnt in family_rows],
        )

        # Verdicts by kit match
        kit_rows = s.execute(
            select(orm.VerdictRow.kit_match, func.count())
            .where(orm.VerdictRow.kit_match.is_not(None))
            .group_by(orm.VerdictRow.kit_match)
        ).all()
        _emit(
            "spoofvane_verdicts_by_kit",
            "Verdicts by matched phishing kit",
            "gauge",
            [({"kit": kit}, float(cnt)) for kit, cnt in kit_rows],
        )

        # Discovered suspects by source
        src_rows = s.execute(
            select(orm.SuspectURLRow.source, func.count()).group_by(orm.SuspectURLRow.source)
        ).all()
        _emit(
            "spoofvane_suspects_total",
            "Discovered suspect URLs by source",
            "gauge",
            [({"source": src}, float(cnt)) for src, cnt in src_rows],
        )

        # Bright Data spend by kind (USD)
        cost_rows = s.execute(
            select(orm.CostEventRow.kind, func.coalesce(func.sum(orm.CostEventRow.usd_amount), 0.0))
            .group_by(orm.CostEventRow.kind)
        ).all()
        _emit(
            "spoofvane_brightdata_spend_usd",
            "Cumulative Bright Data spend in USD by API kind",
            "gauge",
            [({"kind": kind}, round(float(amt), 6)) for kind, amt in cost_rows],
        )

        # Feedback events by outcome (active-learning signal volume)
        fb_rows = s.execute(
            select(orm.FeedbackEventRow.outcome, func.count()).group_by(orm.FeedbackEventRow.outcome)
        ).all()
        _emit(
            "spoofvane_feedback_total",
            "Analyst feedback events by outcome",
            "gauge",
            [({"outcome": out}, float(cnt)) for out, cnt in fb_rows],
        )

        # Tenant + API key counts
        tenant_count = s.scalar(select(func.count()).select_from(orm.TenantRow)) or 0
        key_count = s.scalar(
            select(func.count()).select_from(orm.ApiKeyRow).where(orm.ApiKeyRow.revoked_at.is_(None))
        ) or 0
        _emit("spoofvane_tenants_total", "Total tenants", "gauge", [({}, float(tenant_count))])
        _emit("spoofvane_active_api_keys_total", "Active (non-revoked) API keys", "gauge", [({}, float(key_count))])

    return "\n".join(lines) + "\n"
