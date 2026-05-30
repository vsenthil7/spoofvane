"""W5 IdP validator: tests leaked creds against a tenant IdP directory.

CRITICAL: validation and lockout are SEPARATE switches. validate_exposure()
sets `validated` (does this identity exist in the tenant?) WITHOUT locking the
account. Lockout is an explicit, separately-gated admin action (lock_account),
never automatic — the Flare pattern.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import CredExposure


@dataclass
class IdpValidator:
    """A minimal IdP directory of known tenant identities (synthetic in tests)."""
    known_identities: set[str] = field(default_factory=set)

    def validate(self, exposure: CredExposure) -> CredExposure:
        """Set `validated` if the identity exists in the tenant. Does NOT lock."""
        exposure.validated = exposure.identity.lower() in {i.lower() for i in self.known_identities}
        # A validated exposure (real account) is higher risk than a random hit.
        if exposure.validated:
            exposure.risk = round(min(1.0, exposure.risk + 0.2), 4)
        return exposure

    def lock_account(self, exposure: CredExposure, admin_confirmed: bool) -> CredExposure:
        """SEPARATE explicit admin action. Only locks when admin_confirmed=True
        AND the exposure is validated. Never automatic."""
        if not admin_confirmed:
            raise PermissionError("account lockout requires explicit admin confirmation")
        if not exposure.validated:
            raise ValueError("cannot lock an unvalidated exposure")
        exposure.locked = True
        return exposure


def validate_exposure(exposure: CredExposure, known_identities: set[str]) -> CredExposure:
    return IdpValidator(known_identities=known_identities).validate(exposure)
