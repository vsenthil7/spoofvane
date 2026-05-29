"""W2 app-store engine: runs all store adapters + correlates cross-store clones."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .base import AppStoreAdapter, AppFinding, STORES


@dataclass
class AppStoreEngine:
    stores: tuple[str, ...] = STORES

    def search(self, brand_name: str, brand_icon_hash: str) -> list[AppFinding]:
        out: list[AppFinding] = []
        for s in self.stores:
            out.extend(AppStoreAdapter(s).search(brand_name, brand_icon_hash))
        out.sort(key=lambda f: f.app_clone_signal, reverse=True)
        return out

    def correlate_cross_store(self, findings: list[AppFinding]) -> dict[str, list[str]]:
        """Identical icon hashes across stores => one clone cluster."""
        by_icon: dict[str, list[str]] = defaultdict(list)
        for f in findings:
            by_icon[f.icon_hash].append(f.store)
        return {h: stores for h, stores in by_icon.items() if len(stores) > 1}


def search_all_stores(brand_name: str, brand_icon_hash: str) -> list[AppFinding]:
    return AppStoreEngine().search(brand_name, brand_icon_hash)
