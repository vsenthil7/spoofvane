"""W7 asset discovery: pivot from a seed domain via passive DNS + cert + WHOIS.

Reuses the discovery/cert_stream + inspection/whois_enricher idea. Returns an
input-dependent asset inventory (distinct seed domains => distinct assets), with
some assets flagged as low-owner-confidence shadow IT.
"""
from __future__ import annotations

from .base import Asset, Exposure, EasmMode, get_easm_mode, seed
from .exposure_scoring import score_exposure

_EXPOSURE_KINDS = [
    ("expired_cert", "TLS certificate expired", 0.7),
    ("open_admin_port", "admin port 8443 reachable from internet", 0.85),
    ("weak_tls", "TLS 1.0 / RC4 cipher accepted", 0.6),
    ("exposed_db", "database port 5432 open", 0.95),
    ("default_creds", "default credentials accepted on login", 1.0),
]


def discover_assets(seed_domain: str) -> list[Asset]:
    """Discover assets pivoting from the seed domain. Replay/mock are
    input-dependent; live scanning is BLOCKED-ENV."""
    if get_easm_mode() == EasmMode.LIVE:  # pragma: no cover - BLOCKED-ENV
        raise NotImplementedError(
            "live EASM scanning needs outbound port/cert probing (BLOCKED-ENV); "
            "replay ships a fixture asset graph")
    base = seed(seed_domain)
    n = 3 + (base % 4)  # 3..6 assets
    assets: list[Asset] = []
    name = seed_domain.split(".")[0]
    for i in range(n):
        s = seed(seed_domain, str(i))
        # Subdomain hosts pivoted from the seed.
        host = f"{['www','api','vpn','legacy','dev','mail'][i % 6]}.{seed_domain}"
        owner_conf = round(0.5 + (s % 50) / 100, 3)
        shadow = owner_conf < 0.65  # low confidence = possible shadow IT
        exposures: list[Exposure] = []
        n_exp = s % 3  # 0..2 exposures
        for j in range(n_exp):
            k = _EXPOSURE_KINDS[(s >> (j + 1)) % len(_EXPOSURE_KINDS)]
            exposures.append(Exposure(kind=k[0], detail=k[1], severity=k[2]))
        a = Asset(
            host=host,
            ip=f"{(s % 223) + 1}.{(s >> 4) % 254}.{(s >> 8) % 254}.{(s >> 12) % 254}",
            cert_cn=f"*.{seed_domain}" if s % 2 == 0 else None,
            first_seen=f"2026-0{1 + (s % 5)}-{1 + (s % 27):02d}",
            owner_confidence=owner_conf,
            exposures=exposures,
            is_shadow_it=shadow,
        )
        a.exposure_score = score_exposure(a)
        assets.append(a)
    assets.sort(key=lambda x: x.exposure_score, reverse=True)
    return assets
