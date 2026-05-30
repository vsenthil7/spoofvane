"""v07 W8 — Real-time client-side protection & victim telemetry (net-new).

Memcyco PoSA / Nano Defenders parity — a surface NO other listed competitor
fully matches. A lightweight JS beacon embedded on the REAL site detects when
its assets are loaded from a foreign origin (cloning), reports per-victim visits
to spoofed pages, and (W8b) serves markered/traceable decoy credentials.

* beacon_ingest   — receives beacon events (public, rate-limited).
* clone_detector  — foreign-origin asset load => opens an alert.
* victim_tracker  — per-victim/per-cluster aggregation (attack magnitude).
* decoy_engine    — W8b markered decoy creds (Memcyco pattern).

Decoy/lockout actions are RBAC-gated + audited. No live external action runs
without a human-confirmed path.
"""
from __future__ import annotations

from .beacon_ingest import BeaconEvent, ingest_beacon
from .clone_detector import detect_clone, CloneVerdict
from .victim_tracker import VictimTracker, Incident
from .decoy_engine import DecoyEngine, DecoyCredential

__all__ = [
    "BeaconEvent", "ingest_beacon", "detect_clone", "CloneVerdict",
    "VictimTracker", "Incident", "DecoyEngine", "DecoyCredential",
]
