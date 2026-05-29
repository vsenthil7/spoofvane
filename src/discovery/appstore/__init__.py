"""v07 W2 — Mobile app-store fraud detection.

Deepens mobile_app_store.py into multi-store coverage (Apple, Google Play, and
third-party stores like APKPure/Aptoide). Detects clone apps via icon-vs-brand
pHash and over-broad permission diffs, feeding an `app_clone` signal into
composite.score(). Live store APIs are 🔒 BLOCKED-ENV (replay default).
"""
from __future__ import annotations

from .base import AppFinding, AppStoreAdapter, STORES
from .engine import AppStoreEngine, search_all_stores
from .apk_analyzer import analyze_apk, PermissionRisk
from .developer_reputation import developer_reputation

__all__ = [
    "AppFinding", "AppStoreAdapter", "STORES",
    "AppStoreEngine", "search_all_stores",
    "analyze_apk", "PermissionRisk", "developer_reputation",
]
