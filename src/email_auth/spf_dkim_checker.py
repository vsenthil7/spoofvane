"""W11 SPF/DKIM alignment checker for a single sending source."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AlignmentResult:
    source_ip: str
    header_from: str
    spf_pass: bool
    dkim_pass: bool
    aligned: bool
    verdict: str  # pass | fail
    spoof_risk: float


def check_alignment(source_ip: str, header_from: str, spf_pass: bool,
                    dkim_pass: bool, envelope_from_domain: str | None = None) -> AlignmentResult:
    """A source aligns when SPF or DKIM passes AND (for SPF) the envelope
    domain matches header_from. A spoofing source failing both is high risk."""
    spf_aligned = spf_pass and (
        envelope_from_domain is None or envelope_from_domain.endswith(header_from.split("@")[-1])
    )
    aligned = bool(dkim_pass or spf_aligned)
    verdict = "pass" if aligned else "fail"
    # Risk: failing both is maximal; partial pass is mild.
    if aligned:
        risk = 0.0
    elif spf_pass or dkim_pass:
        risk = 0.5
    else:
        risk = 1.0
    return AlignmentResult(
        source_ip=source_ip, header_from=header_from,
        spf_pass=spf_pass, dkim_pass=dkim_pass, aligned=aligned,
        verdict=verdict, spoof_risk=round(risk, 4),
    )
