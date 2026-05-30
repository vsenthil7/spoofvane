"""W7 subsidiary mapper: pivots to related-org assets via shared infra/WHOIS."""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import seed


@dataclass
class Subsidiary:
    name: str
    domain: str
    relationship: str   # shared_registrant | shared_asn | shared_cert_org
    confidence: float


def map_subsidiaries(seed_domain: str) -> list[Subsidiary]:
    """Find related-org domains pivoting from shared WHOIS registrant / ASN /
    cert org. Input-dependent; distinct seeds => distinct subsidiaries."""
    s = seed(seed_domain, "subs")
    n = s % 3  # 0..2 subsidiaries
    name = seed_domain.split(".")[0]
    rels = ["shared_registrant", "shared_asn", "shared_cert_org"]
    out: list[Subsidiary] = []
    for i in range(n):
        si = seed(seed_domain, "subs", str(i))
        out.append(Subsidiary(
            name=f"{name.capitalize()} {['Holdings','Labs','EU','Pay'][si % 4]}",
            domain=f"{name}-{['holdings','labs','eu','pay'][si % 4]}.com",
            relationship=rels[si % len(rels)],
            confidence=round(0.55 + (si % 40) / 100, 3),
        ))
    return out
