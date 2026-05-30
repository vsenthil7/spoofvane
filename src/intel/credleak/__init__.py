"""v07 W5 — Credential-leak & stealer-log monitoring (net-new).

Flare/Constella core: parse infostealer logs, attribute leaked credentials to a
tenant, and validate against the tenant IdP. CRITICAL DESIGN: validation and
lockout are SEPARATE switches — idp_validator returns a `validated` flag without
auto-locking; lockout is an explicit admin-gated action. Real stealer-log
markets are 🔒 BLOCKED-ENV; replay ships SYNTHETIC fixtures only.
"""
from __future__ import annotations

from .base import CredExposure, ExposureType
from .stealer_log_parser import parse_stealer_log
from .idp_validator import IdpValidator, validate_exposure
from .nhi_detector import detect_nhi, NhiExposure

__all__ = [
    "CredExposure", "ExposureType", "parse_stealer_log",
    "IdpValidator", "validate_exposure", "detect_nhi", "NhiExposure",
]
