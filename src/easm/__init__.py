"""v07 W7 — External Attack-Surface Management (EASM) — net-new.

Recorded Future ASI / ZeroFox ASM parity. Outside-in discovery of the brand's
OWN footprint (shadow IT, forgotten infra) — the inverse of impersonation
hunting. Pivots from a seed domain via passive DNS + cert-graph + WHOIS to find
related assets, scores exposure (expired certs, open admin ports, weak TLS), and
maps subsidiaries. Live scanning is 🔒 BLOCKED-ENV; replay ships a fixture asset
graph.
"""
from __future__ import annotations

from .base import Asset, Exposure, EasmMode, get_easm_mode
from .asset_discovery import discover_assets
from .exposure_scoring import score_exposure, exposure_rank
from .subsidiary_mapper import map_subsidiaries

__all__ = [
    "Asset", "Exposure", "EasmMode", "get_easm_mode",
    "discover_assets", "score_exposure", "exposure_rank", "map_subsidiaries",
]
