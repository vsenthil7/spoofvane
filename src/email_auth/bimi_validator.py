"""W11 BIMI validator: checks DMARC-enforced + VMC presence."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BimiResult:
    domain: str
    bimi_record_present: bool
    dmarc_enforced: bool       # policy quarantine or reject (not none)
    vmc_present: bool          # Verified Mark Certificate
    logo_url: str | None
    valid: bool
    reason: str


def validate_bimi(domain: str, dmarc_policy: str, bimi_record: str | None,
                  vmc_url: str | None) -> BimiResult:
    """BIMI is valid only when a BIMI record exists, DMARC is enforced
    (quarantine/reject), and a VMC is present (Gmail/Apple requirement)."""
    present = bool(bimi_record)
    enforced = dmarc_policy in ("quarantine", "reject")
    vmc = bool(vmc_url)
    logo = None
    if present and bimi_record:
        # extract l= (logo) tag if present
        for part in bimi_record.split(";"):
            part = part.strip()
            if part.startswith("l="):
                logo = part[2:].strip()
    valid = present and enforced and vmc
    if not present:
        reason = "no BIMI DNS record"
    elif not enforced:
        reason = f"DMARC policy '{dmarc_policy}' not enforced (needs quarantine/reject)"
    elif not vmc:
        reason = "no VMC (Verified Mark Certificate)"
    else:
        reason = "valid"
    return BimiResult(domain=domain, bimi_record_present=present, dmarc_enforced=enforced,
                      vmc_present=vmc, logo_url=logo, valid=valid, reason=reason)
