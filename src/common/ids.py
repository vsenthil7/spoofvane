"""Time-ordered identifiers.

We use a simple ULID-style prefix scheme so IDs sort by creation time and
the prefix makes the type obvious in logs.
"""
from __future__ import annotations

import secrets
import time

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford Base32


def _base32_encode(value: int, length: int) -> str:
    out = []
    for _ in range(length):
        out.append(_ALPHABET[value & 0x1F])
        value >>= 5
    return "".join(reversed(out))


def make_id(prefix: str) -> str:
    """Return a new ULID-style ID, e.g. ``brand_01HXYZ...``."""
    ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = secrets.randbits(80)
    return f"{prefix}_{_base32_encode(ts_ms, 10)}{_base32_encode(rand, 16)}"


def brand_id() -> str:
    return make_id("brand")


def suspect_id() -> str:
    return make_id("susp")


def inspection_id() -> str:
    return make_id("insp")


def verdict_id() -> str:
    return make_id("verd")


def alert_id() -> str:
    return make_id("alrt")
