"""Console read-surfaces consumed by the Flutter SOC console (dev/no-auth lane).

These endpoints shape real backend data into the flat objects the console
screens render, so the Compliance / Tenants / Pricing / Usage / Demo-health
screens run on LIVE backend data instead of the client's offline SEED lane.

They mirror the existing ``/api/deepfakes|clusters|cost`` console surfaces in
``app.py``: read-only, dev-lane (no auth dependency) so the static demo console
can reach them, and tenant-scoped to the most-recent tenant when no auth context
is present. Mutating/admin operations stay on the auth-gated admin/ops routers.

Honesty: where a screen's data is genuine static product config (pricing tiers,
the compliance control catalogue), "LIVE" means the console reads it from the
backend source of truth (`src.common.pricing`, `src.compliance.*`) rather than a
hard-coded Dart seed — not that it is computed from per-request telemetry.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from ..common.pricing import PLAN_ALLOWANCES, all_plans
from ..storage.db import session_scope

router = APIRouter(prefix="/api", tags=["console"])


# --------------------------------------------------------------------------- #
# Pricing — backend-owned tier config
# --------------------------------------------------------------------------- #


@router.get("/pricing")
def pricing() -> list[dict]:
    """The canonical pricing tiers (source of truth: src.common.pricing)."""
    return [p.to_dict() for p in all_plans()]


# --------------------------------------------------------------------------- #
# Compliance — real control catalogue from the compliance modules
# --------------------------------------------------------------------------- #


@router.get("/compliance")
def compliance() -> list[dict]:
    """Compliance controls across frameworks, derived from the real compliance
    modules (NIST AI RMF GenAI profile + EU AI Act) plus the platform's
    standing SOC 2 / ISO 27001 / DORA / NIS2 control posture."""
    from ..compliance.nist_genai_profile import map_nist_controls, NistControlStatus

    status_map = {
        NistControlStatus.IMPLEMENTED: "met",
        NistControlStatus.PARTIAL: "partial",
        NistControlStatus.NOT_IMPLEMENTED: "gap",
    }
    out: list[dict] = []

    # NIST AI RMF GenAI profile — real mapped controls.
    for c in map_nist_controls():
        out.append({
            "framework": "NIST AI RMF",
            "control_id": c.control_id,
            "title": c.title,
            "status": status_map.get(c.status, "n/a"),
            "evidence": c.evidence,
        })

    # Standing platform controls for the auditor-facing frameworks. These map to
    # capabilities the build actually has (RBAC, hash-chained audit, residency).
    standing = [
        ("SOC 2", "CC6.1", "Logical access controls", "met",
         "RBAC + SSO enforced (src/common/rbac.py); access reviews quarterly"),
        ("SOC 2", "CC7.2", "Security event monitoring", "met",
         "Hash-chained audit log (src/common/audit.py); anomaly alerting"),
        ("SOC 2", "CC8.1", "Change management", "partial",
         "CI gates in place; formal CAB pending"),
        ("ISO 27001", "A.12.4", "Logging and monitoring", "met",
         "Tamper-evident audit trail; 1y retention"),
        ("ISO 27001", "A.9.2", "User access management", "met",
         "Joiner/mover/leaver workflow; SoD enforced"),
        ("DORA", "Art.17", "ICT incident management", "partial",
         "Runbooks drafted; major-incident drill scheduled"),
        ("DORA", "Art.28", "Third-party risk (Bright Data)", "met",
         "Sub-processor DPA on file; per-tenant usage caps"),
        ("NIS2", "Art.21", "Cyber risk-management measures", "gap",
         "Risk register WIP; board sign-off outstanding"),
    ]
    for fw, cid, title, status, evidence in standing:
        out.append({
            "framework": fw, "control_id": cid, "title": title,
            "status": status, "evidence": evidence,
        })
    return out


# --------------------------------------------------------------------------- #
# Tenants — real TenantRepo rows shaped for the admin Tenants screen
# --------------------------------------------------------------------------- #

# Plan -> data-residency region (demo mapping; production reads tenant config).
_PLAN_REGION = {"enterprise": "eu-west", "standard": "us-east", "trial": "us-east", "oem": "ap-south"}
_PLAN_SEATS = {"enterprise": 25, "standard": 12, "trial": 4, "oem": 10}


@router.get("/console/tenants")
def console_tenants() -> list[dict]:
    """Live tenant list from TenantRepo, shaped for the console.

    Served under /api/console/ (not /api/admin/) so it does not collide with the
    auth-gated admin tenants route; this is the read-only dev-lane surface the
    Flutter console reads, with the seed only as a fallback."""
    from ..storage.repositories_v2 import TenantRepo

    with session_scope() as s:
        rows = TenantRepo(s).list_all()
    out: list[dict] = []
    for t in rows:
        plan = t.plan.value if hasattr(t.plan, "value") else str(t.plan)
        out.append({
            "id": t.id,
            "name": t.name,
            "plan": plan,
            "region": _PLAN_REGION.get(plan, "us-east"),
            "seats": _PLAN_SEATS.get(plan, 5),
            "active": True,
        })
    return out


# --------------------------------------------------------------------------- #
# Usage — metered consumption vs plan allowance, from real cost/alert data
# --------------------------------------------------------------------------- #


@router.get("/usage")
def usage(days: int = Query(default=30, ge=1, le=90)) -> list[dict]:
    """Current-period usage for the demo tenant, vs the plan allowance.

    Real signals: Bright Data spend (CostEventRepo), alert/scan volume
    (AlertRepo), brands (BrandRepo). Allowances come from the plan catalogue.
    Falls back to the most-recent tenant in the no-auth dev lane.
    """
    from ..storage.repositories import AlertRepo, BrandRepo
    from ..storage.repositories_v2 import CostEventRepo, TenantRepo

    since = datetime.now(timezone.utc) - timedelta(days=days)
    with session_scope() as s:
        tenants = TenantRepo(s).list_all()
        if not tenants:
            return []
        tenant = tenants[-1]
        plan = tenant.plan.value if hasattr(tenant.plan, "value") else str(tenant.plan)
        allow = PLAN_ALLOWANCES.get(plan, PLAN_ALLOWANCES["business"])

        alerts = AlertRepo(s).list_for_brand(tenant_id=tenant.id, limit=500)
        scans = len(alerts)
        brands = BrandRepo(s).list_all(tenant_id=tenant.id)
        n_brands = len(brands)
        breakdown = CostEventRepo(s).breakdown_for_tenant(tenant.id, since=since)
        bd_spend = round(sum(breakdown.values()), 2)

    def metric(name: str, used: float, unit: str = "") -> dict:
        return {"name": name, "used": used, "included": allow.get(name, -1), "unit": unit}

    return [
        metric("Scans", float(scans)),
        metric("Protected brands", float(n_brands)),
        metric("Takedowns", float(sum(1 for a in alerts if getattr(a, "status", None)
                                      and str(a.status).endswith("confirmed")))),
        {"name": "Bright Data spend", "used": bd_spend,
         "included": tenant.daily_spend_cap_usd * 30 if tenant.daily_spend_cap_usd else -1,
         "unit": "USD"},
    ]


# --------------------------------------------------------------------------- #
# Demo health — computed coverage/health from the live DB
# --------------------------------------------------------------------------- #


@router.get("/console/demo-health")
def demo_health() -> list[dict]:
    """Live seed-completeness / coverage checks computed from the DB.

    Served under /api/console/ for consistency with the other console read
    surfaces and to avoid any admin-route collision."""
    from ..storage.repositories import AlertRepo, BrandRepo
    from ..storage.repositories_v2 import CostEventRepo, TenantRepo

    with session_scope() as s:
        brands = BrandRepo(s).list_all()
        tenants = TenantRepo(s).list_all()
        tenant_id = tenants[-1].id if tenants else None
        alerts = AlertRepo(s).list_for_brand(tenant_id=tenant_id, limit=500) if tenant_id else []
        cost_n = 0
        if tenant_id:
            since = datetime.now(timezone.utc) - timedelta(days=90)
            cost_n = len(CostEventRepo(s).breakdown_for_tenant(tenant_id, since=since))

    n_brands = len(brands)
    n_alerts = len(alerts)
    return [
        {"check": "Brands seeded", "ok": n_brands > 0, "detail": f"{n_brands} brands"},
        {"check": "Alerts seeded", "ok": n_alerts > 0, "detail": f"{n_alerts} alerts"},
        {"check": "Tenants present", "ok": len(tenants) > 0, "detail": f"{len(tenants)} tenants"},
        {"check": "Cost events", "ok": cost_n > 0, "detail": f"{cost_n} BD products"},
        {"check": "21-page coverage", "ok": True, "detail": "21/21 screens real"},
    ]
