"""
Seed the demo: onboard ``DemoBank`` and run one full pipeline pass.

This is what the live demo runs at t=0 to populate the triage dashboard
with realistic-looking alerts before the judge clicks anything.

Idempotent: if DemoBank already exists, it is reused; the pipeline pass
appends new suspect URLs / alerts.

Usage::

    python -m scripts.seed_demo
"""

from __future__ import annotations

import sys
from pathlib import Path

from src.common.ids import brand_id as gen_brand_id, suspect_id
from src.common.logging import get_logger
from src.common.models import Brand, Source, SuspectURL
from src.common.pipeline import run_pipeline_for_brand
from src.common.settings import get_settings
from src.inspection.browser import get_inspector
from src.storage.db import session_scope
from src.storage.init_db import init_db
from src.storage.repositories import BrandRepo
from src.storage.repositories_v2 import CostEventRepo, TenantRepo
from src.common.tenants import Tenant, TenantPlan

log = get_logger(__name__)


DEMO_BRAND_NAME = "DemoBank"
DEMO_LOGIN_URL = "https://login.demobank.example/signin"
DEMO_TENANT_NAME = "DemoTenant"

# Realistic Bright Data product spend for the cost-attribution screen.
_DEMO_COST_EVENTS = [
    ("serp", 4.21),
    ("unlocker", 9.84),
    ("scraping_browser", 12.50),
    ("residential", 6.10),
    ("web_scraper", 3.40),
    ("datasets", 2.15),
]


def ensure_demo_tenant_costs() -> None:
    """Create a demo tenant (if absent) and record realistic Bright Data cost
    events against it, so /api/cost serves LIVE data instead of empty.
    Idempotent: skips recording if the tenant already has cost events."""
    with session_scope() as s:
        trepo = TenantRepo(s)
        tenant = trepo.get_by_name(DEMO_TENANT_NAME)
        if tenant is None:
            tenant = trepo.create(
                Tenant(
                    id=gen_brand_id(),
                    name=DEMO_TENANT_NAME,
                    plan=TenantPlan.ENTERPRISE,
                    daily_spend_cap_usd=500.0,
                )
            )
            log.info("seed.tenant_created", tenant_id=tenant.id)
        crepo = CostEventRepo(s)
        # Only seed once: if a breakdown already exists, leave it.
        if not crepo.breakdown_for_tenant(tenant.id):
            for kind, usd in _DEMO_COST_EVENTS:
                crepo.record(kind=kind, usd_amount=usd, tenant_id=tenant.id)
            log.info("seed.cost_events", tenant_id=tenant.id, n=len(_DEMO_COST_EVENTS))


def ensure_demo_brand() -> Brand:
    """Create DemoBank if it doesn't exist; return it either way."""
    settings = get_settings()
    settings.ensure_dirs()

    with session_scope() as s:
        existing = BrandRepo(s).get_by_name(DEMO_BRAND_NAME)
        if existing is not None:
            log.info("seed.brand_exists", brand_id=existing.id)
            return existing

    brand = Brand(
        id=gen_brand_id(),
        name=DEMO_BRAND_NAME,
        login_url=DEMO_LOGIN_URL,
        target_country="US",
        brand_keywords=["demobank", "demo-bank", "demo bank"],
        score_threshold=settings.score_threshold_composite,
    )

    # Capture canonical screenshot + DOM via the (mock) inspector
    canonical_suspect = SuspectURL(
        id=suspect_id(),
        brand_id=brand.id,
        url=DEMO_LOGIN_URL,
        source=Source.MANUAL,
        discovery_metadata={"role": "canonical_baseline"},
    )
    inspector = get_inspector()
    canonical = inspector.inspect(brand, canonical_suspect)
    if not canonical.success:
        raise RuntimeError(f"canonical inspection failed: {canonical.error}")
    brand.canonical_screenshot_hash = canonical.screenshot_hash
    brand.canonical_dom_hash = canonical.dom_hash

    with session_scope() as s:
        saved = BrandRepo(s).create(brand)
    log.info("seed.brand_created", brand_id=saved.id)
    return saved


def main() -> int:
    init_db()  # safe to re-run
    brand = ensure_demo_brand()
    ensure_demo_tenant_costs()
    print(f"✓ Brand ready: {brand.name} ({brand.id})")
    print(f"  canonical screenshot: {brand.canonical_screenshot_hash}")
    print(f"  canonical dom:        {brand.canonical_dom_hash}")
    print()

    print("Running pipeline pass…")
    stats = run_pipeline_for_brand(brand.id, max_inspect=100)

    print()
    print("Pipeline complete:")
    print(f"  Suspects discovered:      {stats.suspects_discovered}")
    print(f"  Suspects inspected:       {stats.suspects_inspected}")
    print(f"  Suspects above threshold: {stats.suspects_above_threshold}")
    print(f"  Alerts created:           {stats.alerts_created}")
    print(f"  Errors:                   {stats.errors}")
    print()
    print("Now run: uvicorn src.api.app:app --reload")
    print("Then open: http://127.0.0.1:8000/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
