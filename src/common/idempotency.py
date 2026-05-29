"""G8 — idempotency-key middleware/store.

Stores the response for a given (tenant, idempotency-key) so a retried request
returns the original result instead of re-executing a side-effectful action
(e.g. a duplicate takedown submission).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IdempotencyStore:
    _store: dict[tuple[str, str], Any] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def get(self, tenant_id: str, key: str) -> Any | None:
        with self._lock:
            return self._store.get((tenant_id, key))

    def remember(self, tenant_id: str, key: str, response: Any) -> None:
        with self._lock:
            self._store[(tenant_id, key)] = response

    def execute(self, tenant_id: str, key: str, fn, *args, **kwargs) -> tuple[Any, bool]:
        """Return (result, replayed). Replayed=True if served from cache."""
        existing = self.get(tenant_id, key)
        if existing is not None:
            return existing, True
        result = fn(*args, **kwargs)
        self.remember(tenant_id, key, result)
        return result, False
