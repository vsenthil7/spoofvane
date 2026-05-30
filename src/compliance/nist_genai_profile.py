"""W14 NIST AI RMF Generative-AI profile control mapping."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class NistControlStatus(str, Enum):
    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    NOT_IMPLEMENTED = "not_implemented"


@dataclass
class NistControl:
    control_id: str
    function: str       # GOVERN | MAP | MEASURE | MANAGE
    title: str
    status: NistControlStatus
    evidence: str


# SpoofVane's mapped controls (status reflects what the build actually proves).
_CONTROLS = [
    ("GV-1.1", "GOVERN", "AI risk management policy", NistControlStatus.IMPLEMENTED,
     "docs/TRACEABILITY_MASTER.md governance ledger"),
    ("MP-2.3", "MAP", "AI system categorization", NistControlStatus.IMPLEMENTED,
     "compliance.eu_ai_act.classify_ai_system"),
    ("MS-2.5", "MEASURE", "Model validity & reliability tracked",
     NistControlStatus.IMPLEMENTED, "src/scoring/calibration.py + differential probes"),
    ("MS-2.7", "MEASURE", "AI red-teaming / adversarial testing",
     NistControlStatus.PARTIAL, "negative-case probes; full red-team pending"),
    ("MG-2.2", "MANAGE", "Incident response & provenance",
     NistControlStatus.IMPLEMENTED, "audit hash-chain + compliance.evidence_provenance"),
    ("MS-1.1", "MEASURE", "GenAI content provenance (C2PA)",
     NistControlStatus.IMPLEMENTED, "deepfake.rtc.provenance_c2pa + evidence_provenance"),
]


def map_nist_controls() -> list[NistControl]:
    return [NistControl(*c) for c in _CONTROLS]


def coverage_summary() -> dict:
    controls = map_nist_controls()
    total = len(controls)
    impl = sum(1 for c in controls if c.status == NistControlStatus.IMPLEMENTED)
    partial = sum(1 for c in controls if c.status == NistControlStatus.PARTIAL)
    return {
        "total": total, "implemented": impl, "partial": partial,
        "not_implemented": total - impl - partial,
        "coverage_pct": round(100 * (impl + 0.5 * partial) / total, 1),
    }
