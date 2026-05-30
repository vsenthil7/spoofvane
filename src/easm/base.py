"""W7 EASM base: Asset + Exposure models, mode resolution."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from enum import Enum


class EasmMode(str, Enum):
    LIVE = "live"
    REPLAY = "replay"
    MOCK = "mock"


def get_easm_mode() -> EasmMode:
    return EasmMode(os.getenv("SPOOFVANE_BD_MODE", "replay").lower())


@dataclass
class Exposure:
    kind: str          # expired_cert | open_admin_port | weak_tls | exposed_db | default_creds
    detail: str
    severity: float    # 0..1


@dataclass
class Asset:
    host: str
    ip: str
    cert_cn: str | None
    first_seen: str
    owner_confidence: float       # 0..1 — how sure we are the brand owns this
    exposures: list[Exposure] = field(default_factory=list)
    exposure_score: float = 0.0
    is_shadow_it: bool = False


def seed(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:8], 16)
