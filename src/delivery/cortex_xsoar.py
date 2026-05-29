"""F5 — Cortex XSOAR incident sink (the 5th SIEM/SOAR sink).

Pushes a SpoofVane alert into Palo Alto Cortex XSOAR as an incident via the
incident-create REST API. Live mode POSTs with an API key; replay returns a
deterministic incident id so downstream tests are stable.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


@dataclass
class XsoarIncident:
    incident_id: str
    severity: int
    name: str
    submitted: bool
    dedup_key: str


SEVERITY_MAP = {"phish": 3, "suspicious": 2, "benign": 1}


class CortexXsoarSink:
    def __init__(self, base_url: str = "", api_key: str = "") -> None:
        self.base_url = base_url or os.getenv("XSOAR_BASE_URL", "")
        self.api_key = api_key or os.getenv("XSOAR_API_KEY", "")

    def create_incident(self, alert: dict, *, dry: bool = True) -> XsoarIncident:
        url = alert.get("url", "")
        verdict = alert.get("verdict", "suspicious")
        dedup = hashlib.sha256(url.encode()).hexdigest()[:16]
        name = f"SpoofVane: {verdict} impersonation — {url[:60]}"
        sev = SEVERITY_MAP.get(verdict, 2)
        submitted = False
        if not dry and self.base_url and self.api_key:
            import httpx  # pragma: no cover - live lane
            with httpx.Client(timeout=20) as c:
                r = c.post(f"{self.base_url}/incident",
                           headers={"Authorization": self.api_key},
                           json={"name": name, "severity": sev, "dedup": dedup})
                submitted = r.status_code < 300
        return XsoarIncident(
            incident_id=f"xsoar-{dedup}", severity=sev, name=name,
            submitted=submitted, dedup_key=dedup,
        )
