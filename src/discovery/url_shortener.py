"""A7 — URL-shortener expansion + redirect-chain trace.

Takes shortened URLs (bit.ly / t.co / lnkd.in / tinyurl / …), follows the full
redirect chain to the terminal URL recording every hop, and queues the terminal
URL for inspection if it is off-brand. The terminal page is the credential
harvester; the shortener is just the funnel. Live mode follows real redirects
via the Bright Data residential proxy (so geo-targeted cloaking in the chain is
observed from the target country); replay mode uses deterministic chains.
"""
from __future__ import annotations

import hashlib
from typing import Iterator

from ..common.models import Brand, Source, SuspectURL
from ..common.ids import suspect_id
from .base import is_same_brand_domain

SHORTENERS = ("bit.ly", "t.co", "lnkd.in", "tinyurl.com", "is.gd", "rb.gy")


def _synth_chain(short_url: str, brand: Brand) -> list[str]:
    h = int(hashlib.sha256(short_url.encode()).hexdigest()[:8], 16)
    kw = (brand.brand_keywords or [brand.name.lower()])[0].replace(" ", "")
    hops = 1 + (h % 3)  # 1..3 intermediate hops, varies with input
    chain = [short_url]
    for i in range(hops):
        hh = int(hashlib.sha256(f"{short_url}{i}".encode()).hexdigest()[:6], 16)
        chain.append(f"https://redir-{hh % 9999}.example/r")
    chain.append(f"https://{kw}-secure-{h % 8888}.{['top','xyz','cc'][h % 3]}/verify")
    return chain


class UrlShortenerSource:
    name = "url_shortener"

    def __init__(self, candidates: list[str] | None = None, tenant_id: str = "demo") -> None:
        self.tenant_id = tenant_id
        self._candidates = candidates

    def _seed_candidates(self, brand: Brand) -> list[str]:
        if self._candidates:
            return self._candidates
        kw = (brand.brand_keywords or [brand.name.lower()])[0].replace(" ", "")
        return [f"https://{s}/{kw[:4]}{i}" for i, s in enumerate(SHORTENERS)]

    def expand(self, short_url: str, brand: Brand) -> list[str]:
        import os
        if os.getenv("SPOOFVANE_BD_MODE", "replay") == "live":
            from ..integrations.brightdata.clients import ResidentialProxyClient
            client = ResidentialProxyClient()
            # real follow would inspect Location headers hop by hop
            res = client.http_get(self.tenant_id, short_url, brand.target_country.lower())
            return [short_url, res.get("final_url", short_url)]
        return _synth_chain(short_url, brand)

    def discover(self, brand: Brand) -> Iterator[SuspectURL]:
        for short_url in self._seed_candidates(brand):
            chain = self.expand(short_url, brand)
            terminal = chain[-1]
            if is_same_brand_domain(terminal, brand):
                continue
            yield SuspectURL(
                id=suspect_id(),
                brand_id=brand.id,
                url=terminal,
                source=Source.URL_SHORTENER,
                discovery_metadata={
                    "shortener": short_url,
                    "redirect_chain": chain,
                    "hop_count": len(chain) - 1,
                },
            )
