"""W2 developer reputation: scores a publisher's trustworthiness."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class DeveloperReputation:
    developer: str
    apps_published: int
    account_age_days: int
    verified_publisher: bool
    reputation: float  # 0 (untrusted) .. 1 (trusted)


def developer_reputation(developer: str, official_developer: str | None = None) -> DeveloperReputation:
    """Deterministic, input-dependent reputation. Matching the official
    developer name yields high reputation; unknown devs score low."""
    s = int(hashlib.sha256(developer.encode()).hexdigest()[:8], 16)
    if official_developer and developer.strip().lower() == official_developer.strip().lower():
        return DeveloperReputation(developer, apps_published=12 + (s % 40),
                                   account_age_days=900 + (s % 2000),
                                   verified_publisher=True, reputation=0.95)
    apps = 1 + (s % 6)
    age = s % 400
    verified = (s % 7 == 0)
    rep = min(1.0, 0.15 + (age / 1000) + (0.3 if verified else 0.0))
    return DeveloperReputation(developer, apps_published=apps, account_age_days=age,
                               verified_publisher=verified, reputation=round(rep, 4))
