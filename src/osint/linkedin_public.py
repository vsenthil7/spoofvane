"""Public-profile enrichment (no auth-walled access; ToS-respecting, fixture-backed).

Returns public-surface attributes an attacker could scrape to build an
impersonation profile. Input-dependent so two execs differ.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import ExecInput, OsintMode, get_osint_mode


@dataclass
class PublicProfile:
    exec_name: str
    headline: str
    public_connections: int
    recent_public_posts: list[str] = field(default_factory=list)
    profile_photo_present: bool = True
    impersonation_risk: float = 0.0


class LinkedInPublicSource:
    name = "linkedin_public"

    def enrich(self, exec_in: ExecInput) -> PublicProfile:
        if get_osint_mode() == OsintMode.LIVE:
            return self._live(exec_in)
        return self._replay(exec_in)

    def _live(self, exec_in: ExecInput) -> PublicProfile:  # pragma: no cover - BLOCKED-ENV
        raise NotImplementedError(
            "live public-profile enrichment is fixture-backed only (ToS + BLOCKED-ENV)")

    def _replay(self, exec_in: ExecInput) -> PublicProfile:
        s = exec_in.seed("linkedin")
        conns = 200 + (s % 4800)
        posts = [
            f"{exec_in.company} keynote recap {1 + (s % 9)}",
            f"Thoughts on {['AI','security','growth','hiring'][s % 4]}",
        ][: 1 + (s % 2)]
        # More public surface area -> higher impersonation risk.
        risk = min(1.0, 0.3 + (conns / 5000) * 0.4 + len(posts) * 0.1)
        return PublicProfile(
            exec_name=exec_in.name,
            headline=f"{exec_in.role} at {exec_in.company}",
            public_connections=conns,
            recent_public_posts=posts,
            profile_photo_present=(s % 4 != 0),
            impersonation_risk=round(risk, 3),
        )
