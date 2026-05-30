"""W4 intel base: IntelHit model + source adapter with live/replay/mock.

All fixture content is SYNTHETIC. No real PII, credentials, or dark-web content
is ever shipped.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

SOURCES = (
    "tor_forums", "telegram_channels", "paste_sites", "breach_dumps", "combo_lists",
)


@dataclass
class IntelHit:
    source: str
    channel: str
    snippet: str
    matched_terms: list[str]
    first_seen: str
    risk: float
    dedup_key: str
    is_fresh: bool = True
    actor: str | None = None


def _seed(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:8], 16)


# Synthetic actor handles for the replay lane (NOT real).
_ACTORS = ("ShadowBroker_synthetic", "phantom_synthetic", "darkvendor_synthetic",
           "kit_seller_synthetic", "anon_synthetic")


class DarkWebSource:
    def __init__(self, source: str) -> None:
        if source not in SOURCES:
            raise ValueError(f"unknown intel source {source}")
        self.source = source

    def _mode(self) -> str:
        return os.getenv("SPOOFVANE_BD_MODE", "replay").lower()

    def collect(self, brand: str, terms: list[str]) -> list[IntelHit]:
        if self._mode() == "live":  # pragma: no cover - BLOCKED-ENV
            raise NotImplementedError(
                f"live {self.source} collection needs Tor/Telegram access (BLOCKED-ENV); "
                "replay ships synthetic fixtures only")
        return self._replay(brand, terms)

    def _replay(self, brand: str, terms: list[str]) -> list[IntelHit]:
        base = _seed(self.source, brand)
        n = base % 3  # 0..2 hits per source
        out: list[IntelHit] = []
        for i in range(n):
            s = _seed(self.source, brand, str(i))
            matched = [t for t in terms if (s >> (len(t) % 5)) % 2 == 0] or [brand]
            # Some hits are stale (recycled dumps), some fresh (current combo lists).
            stale = (s % 3 == 0)
            first_seen_year = 2023 if stale else 2026
            risk = 0.4 if stale else min(1.0, 0.6 + 0.1 * len(matched))
            actor = _ACTORS[s % len(_ACTORS)] if self.source in ("tor_forums", "telegram_channels") else None
            # dedup_key is content-stable: same snippet across sources collapses.
            snippet = f"[synthetic] {brand} data offered ({'old' if stale else 'fresh'} batch {s % 99})"
            dedup_key = hashlib.sha256(snippet.encode()).hexdigest()[:16]
            out.append(IntelHit(
                source=self.source,
                channel=f"{self.source}/chan_{s % 50}",
                snippet=snippet,
                matched_terms=sorted(set(matched)),
                first_seen=f"{first_seen_year}-{1 + (s % 12):02d}-{1 + (s % 27):02d}",
                risk=round(risk, 4),
                dedup_key=dedup_key,
                is_fresh=not stale,
                actor=actor,
            ))
        return out
