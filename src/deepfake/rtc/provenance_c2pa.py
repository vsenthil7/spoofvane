"""W10 C2PA provenance: verify content-credentials manifest on media."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class C2paResult:
    has_manifest: bool
    signature_valid: bool
    issuer: str | None
    ai_generated_declared: bool
    trust: str   # trusted | unverified | tampered

    @property
    def provenance_present(self) -> bool:
        return self.has_manifest and self.signature_valid


def verify_c2pa(manifest: dict | None) -> C2paResult:
    """Verify a C2PA manifest. Present + valid signature => trusted provenance;
    present but bad signature => tampered; absent => unverified."""
    if not manifest:
        return C2paResult(False, False, None, False, "unverified")
    sig_valid = bool(manifest.get("signature_valid"))
    issuer = manifest.get("issuer")
    ai_declared = bool(manifest.get("ai_generated"))
    if not sig_valid:
        trust = "tampered"
    else:
        trust = "trusted"
    return C2paResult(
        has_manifest=True, signature_valid=sig_valid, issuer=issuer,
        ai_generated_declared=ai_declared, trust=trust,
    )
