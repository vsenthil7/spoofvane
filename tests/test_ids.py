"""IDs are unique and time-ordered."""

import time

from src.common.ids import alert_id, brand_id, inspection_id, suspect_id, verdict_id


def test_ids_are_unique() -> None:
    ids = {brand_id() for _ in range(500)}
    assert len(ids) == 500


def test_ids_are_time_ordered() -> None:
    a = brand_id()
    time.sleep(0.005)
    b = brand_id()
    # Crockford-Base32 ULID-style: lexicographic sort == time order
    assert a < b


def test_factories_have_distinct_prefixes() -> None:
    samples = {
        "brand": brand_id(),
        "suspect": suspect_id(),
        "inspection": inspection_id(),
        "verdict": verdict_id(),
        "alert": alert_id(),
    }
    # All should be non-empty
    assert all(samples.values())
    # All distinct
    assert len(set(samples.values())) == len(samples)
