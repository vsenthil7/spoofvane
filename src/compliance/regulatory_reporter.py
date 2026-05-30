"""W14 regulatory reporter: GDPR 72h / DORA / NIS2 breach-report builder."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class RegulatoryReport:
    regime: str               # gdpr | dora | nis2
    incident_id: str
    detected_at: str
    deadline_at: str
    hours_to_deadline: float
    notifiable: bool
    required_fields: list[str]


_DEADLINE_HOURS = {"gdpr": 72, "dora": 4, "nis2": 24}
_FIELDS = {
    "gdpr": ["nature_of_breach", "categories_of_data", "approximate_records",
             "likely_consequences", "measures_taken", "dpo_contact"],
    "dora": ["incident_classification", "affected_services", "impact_assessment",
             "remediation_status"],
    "nis2": ["incident_severity", "cross_border_impact", "service_continuity",
             "indicators_of_compromise"],
}


def build_breach_report(regime: str, incident_id: str, detected_at: str,
                        affected_records: int, involves_personal_data: bool) -> RegulatoryReport:
    """Build a regulatory breach report stub with the regime's deadline +
    required fields. Notifiable depends on regime + personal-data involvement."""
    regime = regime.lower()
    if regime not in _DEADLINE_HOURS:
        raise ValueError(f"unknown regulatory regime {regime}")
    dt = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
    hours = _DEADLINE_HOURS[regime]
    deadline = dt + timedelta(hours=hours)
    # GDPR notifiable only if personal data involved; DORA/NIS2 by service impact.
    notifiable = involves_personal_data if regime == "gdpr" else affected_records > 0
    return RegulatoryReport(
        regime=regime, incident_id=incident_id, detected_at=detected_at,
        deadline_at=deadline.isoformat(), hours_to_deadline=float(hours),
        notifiable=notifiable, required_fields=list(_FIELDS[regime]),
    )
