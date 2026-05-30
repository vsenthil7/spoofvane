"""W9 exec dossier: aggregates v06 osint + W9 physical/doxxing into one
exposure dossier, and bridges into the W12 impersonation graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..osint.base import ExecInput
from ..osint.redaction import RedactionRecommender
from ..osint.data_broker import DataBrokerSource
from .physical_threat import scan_physical_threats, PhysicalThreat
from .doxxing_monitor import scan_doxxing, DoxxingExposure


@dataclass
class ExecDossier:
    exec_name: str
    company: str
    broker_exposure: float
    redaction_items: list[str]
    physical_threats: list[PhysicalThreat]
    doxxing: DoxxingExposure
    overall_risk: float


def build_exec_dossier(name: str, company: str, role: str = "Executive") -> ExecDossier:
    exec_in = ExecInput(name=name, company=company, role=role)
    broker = DataBrokerSource().check(exec_in)
    redaction = RedactionRecommender().recommend(exec_in)
    physical = scan_physical_threats(name, company)
    dox = scan_doxxing(name, company)
    phys_sev = max((t.severity for t in physical), default=0.0)
    overall = round(min(1.0,
        0.35 * broker.exposure_score + 0.25 * dox.severity +
        0.25 * phys_sev + 0.15 * redaction.overall_exposure), 4)
    return ExecDossier(
        exec_name=name, company=company,
        broker_exposure=broker.exposure_score,
        redaction_items=redaction.ranked_items,
        physical_threats=physical,
        doxxing=dox,
        overall_risk=overall,
    )
