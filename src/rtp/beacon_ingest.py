"""W8 beacon ingest: receives + validates beacon events from the sv-beacon.js
snippet embedded on the real site."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class BeaconEvent:
    site: str               # the real protected site the beacon belongs to
    origin: str             # the origin the page was actually served from
    fingerprint: str        # device fingerprint (privacy-scoped hash)
    ts: str
    cluster: str | None = None   # URL-cluster the spoof belongs to
    user_agent: str = ""

    @property
    def is_foreign_origin(self) -> bool:
        """The page is foreign if its serving origin host != the real site host."""
        return _host(self.origin) != _host(self.site)


def _host(url: str) -> str:
    u = url.lower().split("//")[-1]
    return u.split("/")[0]


def ingest_beacon(raw: dict) -> BeaconEvent:
    """Validate + normalize a raw beacon POST body into a BeaconEvent."""
    site = str(raw.get("site", "")).strip()
    origin = str(raw.get("origin", "")).strip()
    if not site or not origin:
        raise ValueError("beacon requires both 'site' and 'origin'")
    fp = str(raw.get("fingerprint", ""))
    # Hash the fingerprint so we never store the raw device signal.
    fp_hash = hashlib.sha256(fp.encode()).hexdigest()[:16] if fp else "anon"
    return BeaconEvent(
        site=site, origin=origin, fingerprint=fp_hash,
        ts=str(raw.get("ts", "")), cluster=raw.get("cluster"),
        user_agent=str(raw.get("ua", ""))[:200],
    )
