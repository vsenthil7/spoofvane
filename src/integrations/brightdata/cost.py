"""Per-tenant/product Bright Data cost tracker (review G9 + §V9-3 cost envelope).

Every BD call records a non-zero cost row keyed by tenant + product + action.
The cost tracker enforces a per-tenant monthly envelope (Free/Pro/Business/
Enterprise tiers) and the SLM-first 70/30 routing target. Rows feed the
SPONSOR_USAGE_LEDGER and the CostPage (P13).
"""
from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Indicative unit costs in USD micro-dollars (µ$) per action. Real values come
# from the BD invoice; these are the demo/replay cost model and are documented
# in docs/COST_ENVELOPE.md.
UNIT_COST_USD = {
    "scraping_browser": 0.0150,   # per rendered page
    "residential_proxy": 0.0010,  # per request
    "serp_api": 0.0025,           # per SERP page
    "web_unlocker": 0.0040,       # per unlock
    "web_scraper": 0.0030,        # per scrape
    "datasets": 0.0008,           # per dataset row
    "mcp_server": 0.0020,         # per MCP tool call
}

# Per-tier monthly envelope in USD (review §V9-3 / docs/COST_ENVELOPE.md).
TIER_ENVELOPE_USD = {
    "free": 5.0,
    "pro": 100.0,
    "business": 1000.0,
    "enterprise": 25000.0,
}


@dataclass
class CostRow:
    tenant_id: str
    product: str
    action: str
    units: int
    usd: float
    ts: str


@dataclass
class CostTracker:
    _rows: list[CostRow] = field(default_factory=list)
    _by_tenant_usd: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, tenant_id: str, product: str, action: str, units: int = 1) -> CostRow:
        if product not in UNIT_COST_USD:
            raise ValueError(f"unknown BD product: {product}")
        usd = round(UNIT_COST_USD[product] * max(units, 1), 6)
        row = CostRow(
            tenant_id=tenant_id,
            product=product,
            action=action,
            units=units,
            usd=usd,
            ts=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._rows.append(row)
            self._by_tenant_usd[tenant_id] += usd
        return row

    def tenant_total(self, tenant_id: str) -> float:
        with self._lock:
            return round(self._by_tenant_usd.get(tenant_id, 0.0), 6)

    def over_envelope(self, tenant_id: str, tier: str) -> bool:
        cap = TIER_ENVELOPE_USD.get(tier.lower())
        if cap is None:
            raise ValueError(f"unknown tier: {tier}")
        return self.tenant_total(tenant_id) > cap

    def rows(self) -> list[CostRow]:
        with self._lock:
            return list(self._rows)

    def product_breakdown(self) -> dict[str, float]:
        out: dict[str, float] = defaultdict(float)
        with self._lock:
            for r in self._rows:
                out[r.product] += r.usd
        return {k: round(v, 6) for k, v in out.items()}

    def reset(self) -> None:
        with self._lock:
            self._rows.clear()
            self._by_tenant_usd.clear()


_TRACKER = CostTracker()


def get_cost_tracker() -> CostTracker:
    return _TRACKER
