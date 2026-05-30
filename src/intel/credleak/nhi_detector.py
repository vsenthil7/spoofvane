"""W5 NHI detector: non-human identity exposure (API keys, OAuth, service accts).

Scans leaked text for exposed machine credentials — a fast-growing leak class
that traditional credential monitoring misses.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .base import CredExposure, ExposureType

# Detection patterns for common non-human-identity secret formats (synthetic-safe).
_NHI_PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_pat": re.compile(r"ghp_[0-9A-Za-z]{36}"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "slack_token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "private_key_block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}


@dataclass
class NhiExposure:
    kind: str
    match_preview: str
    risk: float


def detect_nhi(text: str) -> list[NhiExposure]:
    out: list[NhiExposure] = []
    for kind, pat in _NHI_PATTERNS.items():
        for m in pat.finditer(text):
            tok = m.group(0)
            # Redacted preview — never echo the full secret.
            preview = tok[:6] + "…" + tok[-2:] if len(tok) > 10 else "…"
            out.append(NhiExposure(kind=kind, match_preview=preview, risk=0.9))
    return out
