"""W13 CrowdStrike Falcon IOC formatter (Custom IOC API schema)."""
from __future__ import annotations

from .common import DeliveryFinding

# Falcon IOC types differ from ours.
_FALCON_TYPE = {
    "domain": "domain",
    "url": "domain",          # Falcon indicators don't take full URLs; use domain
    "ip": "ipv4",
    "cert": "sha256",         # cert sha mapped to sha256 indicator
}

_FALCON_SEVERITY = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}


def _domain_of(url: str) -> str:
    return url.lower().split("//")[-1].split("/")[0]


def format_falcon_ioc(finding: DeliveryFinding, action: str = "detect") -> dict:
    """Build a CrowdStrike Falcon Custom IOC (indicators v1) payload item."""
    ftype = _FALCON_TYPE.get(finding.ioc_type, "domain")
    value = finding.ioc_value
    if ftype == "domain" and "//" in value:
        value = _domain_of(value)
    return {
        "type": ftype,
        "value": value,
        "action": action,                      # detect | prevent | no_action
        "severity": _FALCON_SEVERITY.get(finding.severity, "low"),
        "description": f"SpoofVane {finding.surface} {finding.verdict}: {finding.brand}",
        "platforms": ["windows", "mac", "linux"],
        "tags": ["spoofvane", finding.surface, finding.finding_id],
        "applied_globally": True,
    }
