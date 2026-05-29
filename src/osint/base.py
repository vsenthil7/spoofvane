"""OSINT base: exec input model + mode resolution (live/replay/mock).

Reuses the Bright Data mode convention (SPOOFVANE_BD_MODE) so reviewers
exercise every OSINT source credential-free. A deterministic per-exec seed
makes every source input-dependent (distinct execs -> distinct outputs) while
staying reproducible.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from enum import Enum


class OsintMode(str, Enum):
    LIVE = "live"
    REPLAY = "replay"
    MOCK = "mock"


def get_osint_mode() -> OsintMode:
    return OsintMode(os.getenv("SPOOFVANE_BD_MODE", "replay").lower())


@dataclass
class ExecInput:
    """The protected executive an OSINT source is run against."""
    name: str
    company: str
    role: str = "Executive"
    domain: str | None = None
    aliases: list[str] = field(default_factory=list)

    def seed(self, *extra: str) -> int:
        """Deterministic per-exec seed; varies with name+company+extra."""
        blob = "|".join([self.name.lower(), self.company.lower(), *extra])
        return int(hashlib.sha256(blob.encode()).hexdigest()[:8], 16)
