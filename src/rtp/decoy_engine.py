"""W8b decoy engine: issues markered/traceable decoy credentials.

When a clone is detected, the real site can serve markered decoy credentials
that render stolen creds useless AND identify the attacker on reuse (Memcyco
pattern). Decoy issuance + reuse-detection are RBAC-gated + audited; this module
provides the mechanism, the API layer enforces the gate.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field


@dataclass
class DecoyCredential:
    username: str
    marker: str          # embedded traceable marker
    issued_for_cluster: str
    issued_ts: str

    def matches(self, presented_username: str) -> bool:
        return presented_username == self.username


@dataclass
class DecoyEngine:
    _issued: dict[str, DecoyCredential] = field(default_factory=dict)

    def issue(self, cluster: str, admin_confirmed: bool = False) -> DecoyCredential:
        """Issue a markered decoy credential for a spoof cluster.
        Serving decoys to live traffic is an audited action; the mechanism is
        always available, but live serve requires the gated API path."""
        marker = secrets.token_hex(8)
        # Deterministic-looking but unique decoy username carrying the marker.
        uname = f"svc_{marker[:6]}@decoy.local"
        from datetime import datetime, timezone
        cred = DecoyCredential(
            username=uname, marker=marker, issued_for_cluster=cluster,
            issued_ts=datetime.now(timezone.utc).isoformat(),
        )
        self._issued[uname] = cred
        return cred

    def detect_reuse(self, presented_username: str) -> DecoyCredential | None:
        """If an attacker reuses a decoy credential, identify which decoy +
        which cluster it traces back to."""
        return self._issued.get(presented_username)

    def is_decoy(self, presented_username: str) -> bool:
        return presented_username in self._issued
