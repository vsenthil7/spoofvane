"""G7 — per-tenant token-bucket rate limiter."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    capacity: float
    refill_per_sec: float
    tokens: float
    last: float


class TokenBucketRateLimiter:
    def __init__(self, capacity: int = 100, refill_per_sec: float = 10.0) -> None:
        self.capacity = capacity
        self.refill = refill_per_sec
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return time.monotonic()

    def allow(self, tenant_id: str, cost: float = 1.0) -> bool:
        with self._lock:
            b = self._buckets.get(tenant_id)
            now = self._now()
            if b is None:
                b = _Bucket(self.capacity, self.refill, self.capacity, now)
                self._buckets[tenant_id] = b
            elapsed = now - b.last
            b.tokens = min(b.capacity, b.tokens + elapsed * b.refill_per_sec)
            b.last = now
            if b.tokens >= cost:
                b.tokens -= cost
                return True
            return False

    def remaining(self, tenant_id: str) -> float:
        with self._lock:
            b = self._buckets.get(tenant_id)
            return b.tokens if b else float(self.capacity)
