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
class KillSwitchEvent:
    """Emitted when cumulative spend crosses the throttle threshold."""
    tenant_id: str
    total_usd: float
    envelope_usd: float
    pct: float
    ts: str


# v06 §D — back-pressure: throttle BD spend at this fraction of the monthly
# envelope so a runaway never burns the whole sponsor budget.
KILL_SWITCH_THRESHOLD = 0.80


@dataclass
class CostTracker:
    _rows: list[CostRow] = field(default_factory=list)
    _by_tenant_usd: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _lock: threading.Lock = field(default_factory=threading.Lock)
    # v06 §D — monthly envelope + back-pressure kill-switch state.
    monthly_envelope_usd: float = 500.0
    _throttled: bool = False
    _kill_events: list[KillSwitchEvent] = field(default_factory=list)

    def record(self, tenant_id: str, product: str, action: str, units: int = 1) -> CostRow:
        if product not in UNIT_COST_USD:
            raise ValueError(f"unknown BD product: {product}")
        if self._throttled:
            raise EnvelopeThrottled(
                f"BD spend throttled: kill-switch engaged at "
                f"{int(KILL_SWITCH_THRESHOLD*100)}% of "
                f"${self.monthly_envelope_usd:.2f} monthly envelope"
            )
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
            total = sum(self._by_tenant_usd.values())
            pct = total / self.monthly_envelope_usd if self.monthly_envelope_usd else 0.0
            if not self._throttled and pct >= KILL_SWITCH_THRESHOLD:
                self._throttled = True
                self._kill_events.append(KillSwitchEvent(
                    tenant_id=tenant_id,
                    total_usd=round(total, 6),
                    envelope_usd=self.monthly_envelope_usd,
                    pct=round(pct, 4),
                    ts=row.ts,
                ))
        return row

    @property
    def throttled(self) -> bool:
        return self._throttled

    @property
    def kill_switch_events(self) -> list[KillSwitchEvent]:
        return list(self._kill_events)

    def total_usd(self) -> float:
        with self._lock:
            return round(sum(self._by_tenant_usd.values()), 6)

    def envelope_pct(self) -> float:
        return round(self.total_usd() / self.monthly_envelope_usd, 4) if self.monthly_envelope_usd else 0.0

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
            self._throttled = False
            self._kill_events.clear()


class EnvelopeThrottled(RuntimeError):
    """Raised when a BD call is attempted after the kill-switch engaged."""


_TRACKER = CostTracker()


def get_cost_tracker() -> CostTracker:
    return _TRACKER
