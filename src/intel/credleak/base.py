"""W5 credleak base: CredExposure model + exposure types. SYNTHETIC only."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExposureType(str, Enum):
    CREDENTIAL = "credential"   # username + password
    SESSION = "session"         # session cookie / token
    NHI = "nhi"                 # non-human identity: API key, OAuth, service acct


@dataclass
class CredExposure:
    identity: str               # the leaked identity (email / username / key id)
    source: str                 # stealer log family / combo list (synthetic)
    exposure_type: ExposureType
    validated: bool = False     # matches a live tenant identity? (set by idp_validator)
    locked: bool = False        # lockout is a SEPARATE explicit admin action
    password_present: bool = False
    session_cookie_present: bool = False
    first_seen: str = ""
    risk: float = 0.0
