"""v06 §F / v07 W9 — OSINT exec-protection surface.

Outside-in intelligence on a protected executive: SEC filings, public profile
enrichment, podcast/transcript mentions, data-broker exposure, and a redaction
recommender. Mirrors the Bright Data live/replay/mock mode convention so every
module runs credential-free in replay and marks live paths 🔒 BLOCKED-ENV.

Every module is REAL by the depth doctrine: two materially different exec
inputs produce two materially different, correct outputs (see
tests/depth/test_osint.py).
"""
from __future__ import annotations

from .base import ExecInput, OsintMode, get_osint_mode

__all__ = ["ExecInput", "OsintMode", "get_osint_mode"]
