"""v06 §D Gate 4 — BD cost-envelope + back-pressure kill-switch depth probe.

Drives a synthetic 90-alert run through the cost ledger, asserts per-product
spend sums correctly and the total respects a configurable monthly envelope,
and proves the kill-switch flips on the 79% -> 81% crossing (beyond-spec
back-pressure). Emits a per-product breakdown in the assertion message.
"""
from __future__ import annotations

import pytest

from src.integrations.brightdata.cost import (
    CostTracker, KILL_SWITCH_THRESHOLD, EnvelopeThrottled, UNIT_COST_USD,
)

# One "alert" exercises a realistic spread of BD products.
ALERT_PRODUCT_MIX = [
    ("serp_api", "search", 1),
    ("scraping_browser", "render", 1),
    ("web_unlocker", "unlock", 1),
    ("residential_proxy", "resolve_dns", 1),
    ("datasets", "whois", 1),
]


def test_90_alert_run_sums_and_stays_under_envelope():
    # Generous envelope so the run completes without throttling.
    t = CostTracker(monthly_envelope_usd=500.0)
    for i in range(90):
        for product, action, units in ALERT_PRODUCT_MIX:
            t.record(f"tenant_demo", product, action, units=units)

    breakdown = t.product_breakdown()
    # Per-product spend equals unit_cost * count(90) for each product used once/alert.
    for product, _, _ in ALERT_PRODUCT_MIX:
        expected = round(UNIT_COST_USD[product] * 90, 6)
        assert breakdown[product] == pytest.approx(expected), (
            f"{product} spend {breakdown[product]} != expected {expected}; "
            f"full breakdown={breakdown}"
        )
    total = t.total_usd()
    assert total < 500.0, f"total ${total} should be under envelope; breakdown={breakdown}"
    assert not t.throttled


def test_kill_switch_flips_on_79_to_81_percent_crossing():
    # Tiny envelope so we can drive the crossing precisely with serp_api units.
    # serp_api unit cost = 0.0025; envelope 1.0 USD -> 80% = 0.80 USD = 320 units.
    t = CostTracker(monthly_envelope_usd=1.0)
    unit = UNIT_COST_USD["serp_api"]
    units_to_79 = int((0.79 * 1.0) / unit)  # just under 80%

    t.record("tenant_demo", "serp_api", "search", units=units_to_79)
    assert not t.throttled, f"at {t.envelope_pct():.2%} should NOT be throttled yet"
    assert t.envelope_pct() < KILL_SWITCH_THRESHOLD

    # Add enough to cross 80%.
    t.record("tenant_demo", "serp_api", "search", units=20)
    assert t.throttled, f"at {t.envelope_pct():.2%} kill-switch should be engaged"
    assert len(t.kill_switch_events) == 1
    ev = t.kill_switch_events[0]
    assert ev.pct >= KILL_SWITCH_THRESHOLD


def test_throttled_tracker_refuses_further_spend():
    t = CostTracker(monthly_envelope_usd=0.01)  # trivially small -> trips fast
    t.record("t", "scraping_browser", "render", units=1)  # 0.015 > 0.008 (80%)
    assert t.throttled
    with pytest.raises(EnvelopeThrottled):
        t.record("t", "serp_api", "search", units=1)


def test_reset_clears_kill_switch():
    t = CostTracker(monthly_envelope_usd=0.01)
    t.record("t", "scraping_browser", "render", units=1)
    assert t.throttled
    t.reset()
    assert not t.throttled
    assert t.kill_switch_events == []
    assert t.total_usd() == 0.0
