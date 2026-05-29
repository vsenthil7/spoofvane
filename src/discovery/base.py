"""Discovery-source protocol shared by the SERP, cert-stream, and new-domain feeds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol
from urllib.parse import urlparse

from ..common.models import Brand, SuspectURL


@dataclass(frozen=True)
class DiscoveryRunResult:
    """Outcome of a single discovery pass."""

    source: str
    queued: int
    skipped_same_domain: int
    errors: int


class DiscoverySource(Protocol):
    """A pluggable discovery feed."""

    name: str

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        """Yield SuspectURLs for ``brand``."""
        ...


def is_same_brand_domain(url: str, brand: Brand) -> bool:
    """Return True iff ``url``'s registered domain matches the brand's canonical login domain.

    Used to avoid sending canonical URLs back into the inspection queue.
    """
    canonical_host = urlparse(str(brand.login_url)).hostname or ""
    suspect_host = urlparse(url).hostname or ""
    if not canonical_host or not suspect_host:
        return False
    # Compare the registrable-domain heuristic: last two labels.
    canonical_parts = canonical_host.lower().split(".")
    suspect_parts = suspect_host.lower().split(".")
    return canonical_parts[-2:] == suspect_parts[-2:]
