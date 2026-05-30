"""v07 W9 — Executive / VIP protection suite (builds on v06 src/osint/).

ZeroFox (21k execs + physical), Doppel exec, Bolster exec parity. Adds a managed
protectee registry, geotagged physical-threat monitoring, doxxing detection
(home address / family exposure), and extends the v06 impersonation graph into
the W12 campaign graph. Two distinct execs => distinct exposure dossiers.
Live threat-feed collection is 🔒 BLOCKED-ENV (fixture-backed replay).
"""
from __future__ import annotations

from .vip_registry import VipRegistry, Protectee
from .physical_threat import scan_physical_threats, PhysicalThreat
from .doxxing_monitor import scan_doxxing, DoxxingExposure
from .dossier import build_exec_dossier, ExecDossier

__all__ = [
    "VipRegistry", "Protectee", "scan_physical_threats", "PhysicalThreat",
    "scan_doxxing", "DoxxingExposure", "build_exec_dossier", "ExecDossier",
]
