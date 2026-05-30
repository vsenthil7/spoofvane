"""W4 keyword matcher: brand/domain/exec matching with dedup + freshness.

Implements the Constella pattern — recycled (duplicate) findings are collapsed
by dedup_key, and freshness is verified so a stale recycled dump scores lower
than a current combo list naming the brand.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import IntelHit, DarkWebSource, SOURCES


@dataclass
class MatchResult:
    hits: list[IntelHit]
    deduped_count: int
    fresh_count: int
    stale_count: int


class KeywordMatcher:
    def __init__(self, sources: tuple[str, ...] = SOURCES) -> None:
        self.sources = sources

    def collect_all(self, brand: str, terms: list[str]) -> list[IntelHit]:
        out: list[IntelHit] = []
        for s in self.sources:
            out.extend(DarkWebSource(s).collect(brand, terms))
        return out

    def match(self, brand: str, terms: list[str]) -> MatchResult:
        raw = self.collect_all(brand, terms)
        # Dedup by content-stable key, keeping the freshest instance.
        by_key: dict[str, IntelHit] = {}
        for h in raw:
            existing = by_key.get(h.dedup_key)
            if existing is None or (h.is_fresh and not existing.is_fresh):
                by_key[h.dedup_key] = h
        deduped = sorted(by_key.values(), key=lambda h: (h.is_fresh, h.risk), reverse=True)
        return MatchResult(
            hits=deduped,
            deduped_count=len(raw) - len(deduped),
            fresh_count=sum(1 for h in deduped if h.is_fresh),
            stale_count=sum(1 for h in deduped if not h.is_fresh),
        )


def match_keywords(brand: str, terms: list[str]) -> MatchResult:
    return KeywordMatcher().match(brand, terms)
