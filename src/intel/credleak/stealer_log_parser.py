"""W5 stealer-log parser: parse infostealer log lines into CredExposures.

Parses the common stealer-log format (URL:USER:PASS plus cookie blocks).
SYNTHETIC input only — never ingest real logs here.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .base import CredExposure, ExposureType


def _risk(exposure_type: ExposureType, has_cookie: bool) -> float:
    base = {ExposureType.CREDENTIAL: 0.6, ExposureType.SESSION: 0.8,
            ExposureType.NHI: 0.9}[exposure_type]
    return round(min(1.0, base + (0.15 if has_cookie else 0.0)), 4)


def parse_stealer_log(log_text: str, source: str = "synthetic_stealer") -> list[CredExposure]:
    """Parse lines of form `https://host/path:user@dom:password` and optional
    `COOKIE host=...` lines into CredExposures. Two-pass so a COOKIE line affects
    credential lines regardless of ordering."""
    lines = [raw.strip() for raw in log_text.splitlines()]
    lines = [l for l in lines if l and not l.startswith("#")]

    # Pass 1: collect cookie hosts.
    cookies_by_host: dict[str, bool] = {}
    for line in lines:
        if line.upper().startswith("COOKIE"):
            parts = line.split("=", 1)
            if len(parts) == 2:
                cookies_by_host[parts[1].strip()] = True

    # Pass 2: parse credential lines.
    exposures: list[CredExposure] = []
    for line in lines:
        if line.upper().startswith("COOKIE"):
            continue
        bits = line.rsplit(":", 2)
        if len(bits) != 3:
            continue
        url, user, pwd = bits
        host = url.split("//")[-1].split("/")[0]
        has_cookie = cookies_by_host.get(host, False)
        etype = ExposureType.SESSION if has_cookie else ExposureType.CREDENTIAL
        seed = int(hashlib.sha256(f"{user}{host}".encode()).hexdigest()[:8], 16)
        exposures.append(CredExposure(
            identity=user,
            source=source,
            exposure_type=etype,
            password_present=bool(pwd),
            session_cookie_present=has_cookie,
            first_seen=f"2026-0{1 + (seed % 5)}-{1 + (seed % 27):02d}",
            risk=_risk(etype, has_cookie),
        ))
    return exposures
