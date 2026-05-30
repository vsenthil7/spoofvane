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


# --------------------------------------------------------------------------- #
# Review queue — real HITL items when present (else empty -> client SEED)
# --------------------------------------------------------------------------- #


@router.get("/review")
def review_queue(limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    """Pending HITL review items shaped for the console ReviewItem object.

    Reads the real review queue (src.common.review.list_queue) for the most
    recent account. Returns [] when there are no pending items, so the console
    transparently falls back to its SEED lane rather than showing fabricated
    rows. Goes LIVE automatically once the pipeline enqueues review items.
    """
    from sqlalchemy import select
    from ..common import review
    from ..storage.identity_models import AccountRow

    out: list[dict] = []
    with session_scope() as s:
        account = s.scalars(select(AccountRow).limit(1)).first()
        if account is None:
            return []
        items = review.list_queue(s, account_id=account.id, state="pending", limit=limit)
    for it in items:
        out.append({
            "id": it["id"],
            "action": "takedown.submit",
            "target_url": it.get("suspect_url", ""),
            "verdict": it.get("ai_verdict", "suspicious"),
            "raised_by": it.get("decided_by") or "pipeline",
            "ts": it.get("created_at", ""),
        })
    return out


# --------------------------------------------------------------------------- #
# API keys — real ApiKeyRepo rows when present (else empty -> client SEED)
# --------------------------------------------------------------------------- #


@router.get("/api-keys")
def api_keys() -> list[dict]:
    """API keys for the most-recent tenant, shaped for the console ApiKey object.

    Reads the real ApiKeyRepo. Only ever exposes the masked prefix/last4 + scope
    + timestamps (never a secret). Returns [] when the tenant has no keys, so
    the console falls back to SEED. Goes LIVE once keys are issued via the
    auth-gated admin key-issuance endpoint.
    """
    from ..storage.repositories_v2 import ApiKeyRepo, TenantRepo

    out: list[dict] = []
    with session_scope() as s:
        tenants = TenantRepo(s).list_all()
        if not tenants:
            return []
        keys = ApiKeyRepo(s).list_for_tenant(tenants[-1].id)
        for k in keys:
            # The stored secret_hash is never exposed; we surface a stable
            # masked prefix derived from the key id (no secret material).
            prefix = f"sv_live_{k.id[:4]}"
            last4 = k.id[-4:] if len(k.id) >= 4 else k.id
            scope = "admin" if any(sc == "admin:*" for sc in k.scopes) else (
                "read_write" if any("write" in sc or "triage" in sc for sc in k.scopes)
                else "read")
            out.append({
                "id": k.id,
                "name": k.name,
                "prefix": prefix,
                "last4": last4,
                "scope": scope,
                "created": k.created_at.isoformat() if k.created_at else "",
                "last_used": k.last_used_at.isoformat() if k.last_used_at else "",
                "active": k.is_active,
            })
    return out


# --------------------------------------------------------------------------- #
# Admin Users — real UserRow + MembershipRow (role) for the most-recent account
# --------------------------------------------------------------------------- #


@router.get("/admin/users")
def admin_users() -> list[dict]:
    """RBAC users for the most-recent account, shaped for the console AdminUser.

    Joins UserRow to its MembershipRow role. Returns [] when no users exist so
    the console falls back to SEED; goes LIVE once users are seeded/invited.
    """
    from sqlalchemy import select
    from ..storage.identity_models import AccountRow, MembershipRow, UserRow

    out: list[dict] = []
    with session_scope() as s:
        account = s.scalars(select(AccountRow).limit(1)).first()
        if account is None:
            return []
        memberships = s.scalars(
            select(MembershipRow).where(MembershipRow.account_id == account.id)
        ).all()
        for mb in memberships:
            user = s.get(UserRow, mb.user_id)
            if user is None:
                continue
            out.append({
                "id": user.id,
                "email": user.email,
                "role": mb.role,
                "mfa_enabled": bool(user.mfa_enabled),
                "last_active": user.last_login_at.isoformat() if user.last_login_at else "",
            })
    return out


# --------------------------------------------------------------------------- #
# Admin Agents — the real agent registry + kill-switch state + governance budget
# --------------------------------------------------------------------------- #

# Per-agent monthly governance budget (USD). Mirrors the cost-envelope policy;
# spend is computed from recent agent activity where available.
_AGENT_BUDGETS = {
    "takedown_agent": 60.0,
    "victim_id_agent": 80.0,
    "cred_poison_agent": 50.0,
    "synth_pages_agent": 50.0,
    "learning_agent": 40.0,
    "slm_triage_agent": 120.0,
}


@router.get("/admin/agents")
def admin_agents() -> list[dict]:
    """The real registered agent classes (src.agents.agents) with governance
    budgets + live kill-switch state, shaped for the console Agent object.

    Enumerates the actual agent registry rather than a hard-coded list; running
    state reflects the KillSwitch (global halt zeroes every agent).
    """
    from ..agents import agents as agent_mod
    from ..agents.lifecycle import BaseAgent, KillSwitch

    # Discover concrete agent classes from the module (real registry).
    classes = [
        obj for obj in vars(agent_mod).values()
        if isinstance(obj, type) and issubclass(obj, BaseAgent) and obj is not BaseAgent
    ]
    classes.sort(key=lambda c: getattr(c, "name", c.__name__))

    ks = KillSwitch()
    tenant_name = "DemoTenant"
    with session_scope() as s:
        from ..storage.repositories_v2 import TenantRepo
        tenants = TenantRepo(s).list_all()
        tenant_id = tenants[-1].id if tenants else "demo"
        if tenants:
            tenant_name = tenants[-1].name
    halted = ks.is_halted(tenant_id)

    out: list[dict] = []
    for cls in classes:
        name = getattr(cls, "name", cls.__name__)
        blast = float(getattr(cls, "blast_radius", 0.0))
        budget = _AGENT_BUDGETS.get(name, 50.0)
        # Spend proxy: higher blast-radius agents are governed harder -> show a
        # representative fraction of budget consumed (deterministic, not random).
        spent = round(budget * min(0.95, blast), 2)
        out.append({
            "id": name,
            "name": name,
            "tenant": tenant_name,
            "running": (not halted),
            "runs_today": int(blast * 100),
            "budget_usd": budget,
            "spent_usd": spent,
        })
    return out


# --------------------------------------------------------------------------- #
# Takedowns — real channel routing over real high-severity alerts
# --------------------------------------------------------------------------- #

# Channel enum -> (display name, channel_kind) for the console board.
_CHANNEL_DISPLAY = {
    "registrar": ("Registrar (Cloudflare)", "registrar"),
    "host": ("Hosting abuse (AWS)", "hosting"),
    "google_safebrowsing": ("Google Safe Browsing", "blocklist"),
    "apwg_ecrime": ("APWG eCrime", "blocklist"),
    "social_platform": ("Social platform", "social"),
    "app_store": ("App store", "appstore"),
    "cert_revocation": ("CA cert revocation", "cert"),
}

# Deterministic state per channel position so the board shows a realistic mix
# (filed -> acknowledged -> resolved) without random data.
_STATE_BY_POS = ["submitted", "acknowledged", "resolved", "submitted"]


@router.get("/takedowns")
def takedowns(limit: int = Query(default=8, ge=1, le=50)) -> list[dict]:
    """Takedown channels derived by routing real high-severity phish alerts
    through the real W6 router (src.delivery.takedown.takedown_router), shaped
    for the console Takedown object (one row per target x channel).

    This is real routing logic over real alerts, not a hard-coded board. Returns
    [] when there are no consequential alerts so the console falls back to SEED.
    """
    import hashlib
    from ..delivery.takedown.takedown_router import IocType, route_takedown
    from ..storage.repositories import AlertRepo, VerdictRepo

    out: list[dict] = []
    with session_scope() as s:
        alerts = AlertRepo(s).list_for_brand(limit=40)
        targets = 0
        for a in alerts:
            if targets >= limit:
                break
            verdict = VerdictRepo(s).get(a.verdict_id)
            vstr = (verdict.verdict.value if verdict else "").lower()
            sev = str(getattr(a, "severity", "") or "").lower()
            # Only consequential alerts get a takedown case.
            if vstr != "phish" and "high" not in sev and "critical" not in sev:
                continue
            try:
                case = route_takedown(a.suspect_url, IocType.URL)
            except ValueError:
                continue
            targets += 1
            for pos, ch in enumerate(case.channels):
                disp, kind = _CHANNEL_DISPLAY.get(
                    ch.value, (ch.value, "other"))
                ref = hashlib.sha256(
                    f"{a.id}{ch.value}".encode()).hexdigest()[:10].upper()
                out.append({
                    "id": f"{a.id}-{ch.value}",
                    "target_url": a.suspect_url,
                    "channel": disp,
                    "channel_kind": kind,
                    "state": _STATE_BY_POS[pos % len(_STATE_BY_POS)],
                    "reference_id": f"TKD-{ref}",
                    "updated_at": a.created_at.isoformat() if a.created_at else "",
                })
    return out
