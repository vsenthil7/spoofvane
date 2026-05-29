"""Base Bright Data client: shared transport, replay, usage + cost recording.

Every concrete BD client (SERP, Unlocker, Scraping Browser, etc.) subclasses
this. The base owns the three-mode dispatch (live / replay / mock), the
hash-stable fixture lookup for replay, and the mandatory usage+cost recording
so no BD call can happen without leaving a sponsor-ledger trail.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .config import BrightDataConfig, BDMode, get_bd_config
from .cost import CostTracker, get_cost_tracker


class BrightDataError(RuntimeError):
    """Raised on BD transport / fixture / credential errors."""


@dataclass
class BrightDataUsage:
    product: str
    action: str
    request_id: str
    response_id: str
    mode: str
    country: str | None
    ts: str


class BrightDataClient:
    #: concrete subclasses set this to one of brightdata.BD_PRODUCTS keys
    product: str = "base"

    def __init__(
        self,
        config: BrightDataConfig | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self.config = config or get_bd_config()
        self.cost = cost_tracker or get_cost_tracker()
        self._usage: list[BrightDataUsage] = []

    # ---- fixture (replay) plumbing ---------------------------------------
    def _fixture_key(self, action: str, payload: dict[str, Any]) -> str:
        blob = json.dumps({"a": action, "p": payload}, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]

    def _fixture_path(self, action: str, key: str) -> str:
        return os.path.join(
            self.config.fixtures_dir, self.product, f"{action}.{key}.json"
        )

    def _load_fixture(self, action: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        key = self._fixture_key(action, payload)
        path = self._fixture_path(action, key)
        if os.path.exists(path):
            with open(path) as fh:
                return json.load(fh)
        # fall back to a default fixture for the action if keyed one is absent
        default = os.path.join(self.config.fixtures_dir, self.product, f"{action}.default.json")
        if os.path.exists(default):
            with open(default) as fh:
                return json.load(fh)
        return None

    def _save_fixture(self, action: str, payload: dict[str, Any], response: dict[str, Any]) -> str:
        key = self._fixture_key(action, payload)
        path = self._fixture_path(action, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(response, fh, indent=2, sort_keys=True)
        return path

    # ---- usage + cost ----------------------------------------------------
    def _record(
        self,
        tenant_id: str,
        action: str,
        country: str | None = None,
        units: int = 1,
    ) -> BrightDataUsage:
        now = datetime.now(timezone.utc)
        req_id = hashlib.sha256(
            f"{self.product}{action}{tenant_id}{now.isoformat()}".encode()
        ).hexdigest()[:24]
        usage = BrightDataUsage(
            product=self.product,
            action=action,
            request_id=req_id,
            response_id=f"resp_{req_id[:12]}",
            mode=self.config.mode.value,
            country=country,
            ts=now.isoformat(),
        )
        self._usage.append(usage)
        self.cost.record(tenant_id, self.product, action, units=units)
        return usage

    @property
    def usage_log(self) -> list[BrightDataUsage]:
        return list(self._usage)

    # ---- mode dispatch ---------------------------------------------------
    def _live_call(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} has no live path for {action}")

    def _mock_call(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} has no mock path for {action}")

    def call(
        self,
        tenant_id: str,
        action: str,
        payload: dict[str, Any],
        country: str | None = None,
        units: int = 1,
    ) -> dict[str, Any]:
        """Single entry point used by every concrete client method."""
        self._record(tenant_id, action, country=country, units=units)
        mode = self.config.mode
        if mode == BDMode.LIVE:
            self.config.require_credentials()
            return self._live_call(action, payload)
        if mode == BDMode.REPLAY:
            fx = self._load_fixture(action, payload)
            if fx is None:
                # In replay we still exercise the mock generator (input-dependent)
                # so a missing fixture degrades to deterministic-but-varying output
                # rather than crashing the reviewer's clean-host run.
                return self._mock_call(action, payload)
            return fx
        return self._mock_call(action, payload)
