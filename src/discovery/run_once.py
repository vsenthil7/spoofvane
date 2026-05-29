"""End-to-end discovery orchestrator.

Run all configured sources for a brand, persist suspect URLs, and return
a summary.

Used both by the CLI (``python -m src.discovery.run_once``) and from the
HTTP layer (``POST /api/discovery/run``).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Sequence

from ..common.logging import get_logger
from ..common.models import Brand
from ..storage.db import session_scope
from ..storage.repositories import BrandRepo, SuspectURLRepo
from .base import DiscoverySource, DiscoveryRunResult
from .cert_stream import CertStreamSource
from .new_domains import NewDomainsSource
from .serp import SERPSource

log = get_logger(__name__)


DEFAULT_SOURCES: dict[str, type[DiscoverySource]] = {
    "serp": SERPSource,
    "cert_stream": CertStreamSource,
    "new_domains": NewDomainsSource,
}


def run_for_brand(brand: Brand, source_names: Sequence[str] | None = None) -> list[DiscoveryRunResult]:
    """Run discovery sources for ``brand`` and persist results.

    Returns one ``DiscoveryRunResult`` per source.
    """
    names = list(source_names) if source_names else list(DEFAULT_SOURCES.keys())
    sources = [DEFAULT_SOURCES[name]() for name in names if name in DEFAULT_SOURCES]
    if not sources:
        log.warning("no_sources_selected", requested=names)
        return []

    summaries: list[DiscoveryRunResult] = []
    with session_scope() as session:
        repo = SuspectURLRepo(session)
        for source in sources:
            queued = 0
            errors = 0
            try:
                for susp in source.discover(brand):
                    try:
                        repo.create(susp)
                        queued += 1
                    except Exception as exc:  # noqa: BLE001
                        errors += 1
                        log.warning("persist_failed", url=susp.url, error=str(exc))
            except Exception as exc:  # noqa: BLE001
                errors += 1
                log.error("source_failed", source=source.name, error=str(exc))

            summaries.append(
                DiscoveryRunResult(
                    source=source.name,
                    queued=queued,
                    skipped_same_domain=0,  # already filtered in-source
                    errors=errors,
                )
            )
            log.info(
                "source_done",
                brand=brand.name,
                source=source.name,
                queued=queued,
                errors=errors,
            )
    return summaries


def _cli() -> None:
    parser = argparse.ArgumentParser(description="DoppelDomain — run a discovery pass")
    parser.add_argument("--brand", required=True, help="Brand name as onboarded")
    parser.add_argument(
        "--sources",
        nargs="+",
        default=None,
        help="Subset of sources to run (default: all)",
    )
    args = parser.parse_args()

    with session_scope() as session:
        brand = BrandRepo(session).get_by_name(args.brand)
    if not brand:
        raise SystemExit(f"Brand not found: {args.brand}")

    results = run_for_brand(brand, args.sources)
    totals: dict[str, int] = defaultdict(int)
    for r in results:
        totals["queued"] += r.queued
        totals["errors"] += r.errors
        print(f"  {r.source:14s} → queued={r.queued} errors={r.errors}")
    print(f"\nTotal queued: {totals['queued']}  Errors: {totals['errors']}")


if __name__ == "__main__":
    _cli()
