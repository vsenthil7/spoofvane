"""Certificate-transparency discovery source.

We tail a certstream-compatible feed of newly-issued TLS certificates.
For every cert whose subject contains a brand-adjacent token we emit
a suspect URL at the root of that domain.

In MOCK_MODE this returns a small fixture batch so the demo populates.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator, Iterator

import httpx

from ..common.ids import suspect_id
from ..common.logging import get_logger
from ..common.models import Brand, Source, SuspectURL
from ..common.settings import get_settings
from .base import is_same_brand_domain

log = get_logger(__name__)


CERTSTREAM_URL = "https://certstream.calidog.io/example.json"  # public sample feed for dev


class CertStreamSource:
    """Tails certificate-transparency entries and emits brand-adjacent hits."""

    name = "cert_stream"

    def __init__(self, max_per_run: int = 50) -> None:
        self.max_per_run = max_per_run

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        settings = get_settings()
        if settings.mock_mode:
            yield from self._mock(brand)
            return

        for cert in self._live(brand):
            for domain in cert.get("all_domains", []):
                if self._is_brand_adjacent(domain, brand) and not is_same_brand_domain(
                    f"https://{domain}", brand
                ):
                    yield SuspectURL(
                        id=suspect_id(),
                        brand_id=brand.id,
                        url=f"https://{domain}",
                        source=Source.CERT_STREAM,
                        discovery_metadata={
                            "ca": cert.get("issuer", {}).get("O"),
                            "not_before": cert.get("not_before"),
                            "all_domains": cert.get("all_domains", [])[:10],
                        },
                    )

    # ─── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _is_brand_adjacent(domain: str, brand: Brand) -> bool:
        d = domain.lower()
        for kw in brand.brand_keywords + [brand.name.lower()]:
            kw = kw.lower().replace(" ", "")
            if kw in d and len(kw) >= 4:
                return True
        return False

    def _live(self, brand: Brand) -> Iterator[dict]:
        """In production this would tail certstream via websocket.

        For the prototype we poll a snapshot endpoint.
        """
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(CERTSTREAM_URL)
                resp.raise_for_status()
                payload = resp.json()
            for entry in payload.get("data", [])[: self.max_per_run]:
                yield entry.get("leaf_cert", {})
        except Exception as exc:  # noqa: BLE001
            log.warning("certstream_fetch_failed", error=str(exc))
            return

    def _mock(self, brand: Brand) -> Iterator[SuspectURL]:
        keyword = (brand.brand_keywords[0] if brand.brand_keywords else brand.name).lower().replace(" ", "")
        fixtures = [
            f"https://{keyword}-secure.com",
            f"https://login-{keyword}.io",
            f"https://{keyword}.verify-account.com",
            f"https://account-{keyword}.app",
        ]
        for url in fixtures:
            if is_same_brand_domain(url, brand):
                continue
            yield SuspectURL(
                id=suspect_id(),
                brand_id=brand.id,
                url=url,
                source=Source.CERT_STREAM,
                discovery_metadata={"ca": "Let's Encrypt", "not_before": str(int(time.time()))},
            )
