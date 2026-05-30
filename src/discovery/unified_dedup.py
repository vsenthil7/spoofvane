"""v07 D7 — unified freshness + dedup across all discovery surfaces.

The same fake entity is often found via multiple surfaces (SERP + cert-stream +
social + dark-web). Without a unifying layer the analyst sees N duplicate
candidates. D7 normalizes a content-stable dedup key per candidate, collapses
duplicates into ONE record that records EVERY source surface that saw it, and
keeps the freshest last_seen timestamp (so a recycled stale sighting never
overwrites a current one).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse


@dataclass
class DiscoveryCandidate:
    """A normalized candidate from any discovery surface."""
    kind: str            # url | domain | social | app | identity
    value: str           # the raw observed value
    surface: str         # which surface saw it (serp, cert_stream, social, ...)
    last_seen: str       # ISO timestamp


@dataclass
class UnifiedCandidate:
    dedup_key: str
    kind: str
    canonical_value: str
    sources: list[str]
    last_seen: str
    sighting_count: int


def _canonical(c: DiscoveryCandidate) -> str:
    """Content-stable canonical form used as the dedup key basis."""
    v = c.value.strip().lower()
    if c.kind in ("url", "domain"):
        host = urlparse(v).hostname if "//" in v else v.split("/")[0]
        host = (host or v).lstrip("www.")
        return host
    if c.kind == "social":
        return v.lstrip("@")
    return v


def _parse_ts(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def unify(candidates: list[DiscoveryCandidate]) -> list[UnifiedCandidate]:
    """Collapse cross-surface duplicates into unified candidates."""
    by_key: dict[str, UnifiedCandidate] = {}
    for c in candidates:
        canon = _canonical(c)
        key = f"{c.kind}:{canon}"
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = UnifiedCandidate(
                dedup_key=key, kind=c.kind, canonical_value=canon,
                sources=[c.surface], last_seen=c.last_seen, sighting_count=1,
            )
        else:
            if c.surface not in existing.sources:
                existing.sources.append(c.surface)
            existing.sighting_count += 1
            # Keep the freshest last_seen.
            if _parse_ts(c.last_seen) > _parse_ts(existing.last_seen):
                existing.last_seen = c.last_seen
    out = list(by_key.values())
    for u in out:
        u.sources.sort()
    out.sort(key=lambda u: (u.sighting_count, _parse_ts(u.last_seen)), reverse=True)
    return out
