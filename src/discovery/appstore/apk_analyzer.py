"""W2 APK analyzer: manifest/permission diff + icon pHash vs brand."""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import SENSITIVE_PERMISSIONS, _icon_clone, _permission_risk


@dataclass
class PermissionRisk:
    sensitive_permissions: list[str]
    over_broad: bool
    icon_clone_score: float
    risk: float


def analyze_apk(permissions: list[str], icon_hash: str, brand_icon_hash: str,
                baseline_permissions: list[str] | None = None) -> PermissionRisk:
    """Flag over-broad permissions vs an optional baseline + icon clone."""
    baseline = set(baseline_permissions or [])
    sensitive = [p for p in permissions if p in SENSITIVE_PERMISSIONS]
    # Over-broad = sensitive perms the official baseline does NOT request.
    extra = [p for p in sensitive if p not in baseline]
    icon = _icon_clone(brand_icon_hash, icon_hash)
    perm_r = _permission_risk(permissions)
    risk = round(min(1.0, 0.5 * icon + 0.5 * perm_r), 4)
    return PermissionRisk(
        sensitive_permissions=sorted(sensitive),
        over_broad=len(extra) > 0,
        icon_clone_score=icon,
        risk=risk,
    )
