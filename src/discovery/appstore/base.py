"""W2 app-store base: AppFinding + multi-store adapter with live/replay/mock."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

STORES = (
    "apple_appstore", "google_play", "apkpure", "aptoide",
    "samsung_galaxy", "amazon_appstore", "huawei_appgallery",
)

# Permissions that are over-broad for a typical brand/banking app.
SENSITIVE_PERMISSIONS = {
    "android.permission.READ_SMS", "android.permission.RECEIVE_SMS",
    "android.permission.SYSTEM_ALERT_WINDOW", "android.permission.BIND_ACCESSIBILITY_SERVICE",
    "android.permission.READ_CONTACTS", "android.permission.RECORD_AUDIO",
    "android.permission.REQUEST_INSTALL_PACKAGES", "android.permission.QUERY_ALL_PACKAGES",
}
BENIGN_PERMISSIONS = {
    "android.permission.INTERNET", "android.permission.CAMERA",
    "android.permission.ACCESS_NETWORK_STATE", "android.permission.VIBRATE",
}


@dataclass
class AppFinding:
    store: str
    app_id: str
    title: str
    developer: str
    icon_hash: str
    permissions: list[str]
    install_count: int
    official: bool = False
    icon_clone_score: float = 0.0
    permission_risk: float = 0.0

    @property
    def app_clone_signal(self) -> float:
        """Combined signal fed into composite.score() as `app_clone`."""
        return round(min(1.0, 0.6 * self.icon_clone_score + 0.4 * self.permission_risk), 4)


def _icon_clone(brand_icon_hash: str, icon_hash: str) -> float:
    if not brand_icon_hash or not icon_hash:
        return 0.0
    if brand_icon_hash == icon_hash:
        return 1.0
    n = min(len(brand_icon_hash), len(icon_hash))
    same = sum(1 for i in range(n) if brand_icon_hash[i] == icon_hash[i])
    return round(same / n, 4) if n else 0.0


def _permission_risk(permissions: list[str]) -> float:
    if not permissions:
        return 0.0
    sensitive = sum(1 for p in permissions if p in SENSITIVE_PERMISSIONS)
    return round(min(1.0, sensitive / 4.0), 4)  # 4+ sensitive perms => max risk


class AppStoreAdapter:
    def __init__(self, store: str) -> None:
        if store not in STORES:
            raise ValueError(f"unknown store {store}")
        self.store = store

    def _mode(self) -> str:
        return os.getenv("SPOOFVANE_BD_MODE", "replay").lower()

    def search(self, brand_name: str, brand_icon_hash: str) -> list[AppFinding]:
        if self._mode() == "live":  # pragma: no cover - BLOCKED-ENV
            raise NotImplementedError(
                f"live {self.store} search needs store API keys (BLOCKED-ENV)")
        return self._replay(brand_name, brand_icon_hash)

    def _replay(self, brand_name: str, brand_icon_hash: str) -> list[AppFinding]:
        base = int(hashlib.sha256(f"{self.store}|{brand_name}".encode()).hexdigest()[:8], 16)
        n = base % 3  # 0..2 apps per store
        out: list[AppFinding] = []
        slug = brand_name.lower().replace(" ", "")
        for i in range(n):
            s = int(hashlib.sha256(f"{self.store}|{brand_name}|{i}".encode()).hexdigest()[:8], 16)
            is_clone = (s % 2 == 0)
            if is_clone:
                icon = brand_icon_hash  # cloned icon
                perms = sorted(BENIGN_PERMISSIONS | {
                    "android.permission.READ_SMS", "android.permission.SYSTEM_ALERT_WINDOW",
                    "android.permission.BIND_ACCESSIBILITY_SERVICE",
                    "android.permission.REQUEST_INSTALL_PACKAGES",
                })
                dev = f"Dev{s % 999}"  # unknown developer
            else:
                icon = hashlib.sha256(f"icon{s}".encode()).hexdigest()
                perms = sorted(BENIGN_PERMISSIONS)
                dev = f"{brand_name} Inc."  # official-looking
            out.append(AppFinding(
                store=self.store,
                app_id=f"com.{slug}.{'app' if not is_clone else f'secure{s % 99}'}",
                title=f"{brand_name}{'' if not is_clone else ' Secure'}",
                developer=dev,
                icon_hash=icon,
                permissions=perms,
                install_count=s % 1000000,
                official=(not is_clone and s % 5 == 0),
                icon_clone_score=_icon_clone(brand_icon_hash, icon),
                permission_risk=_permission_risk(perms),
            ))
        return out
