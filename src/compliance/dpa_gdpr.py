"""W14 DPA/GDPR data-handling record (Article 30 record of processing)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DpaRecord:
    processing_activity: str
    lawful_basis: str
    data_categories: list[str]
    retention_days: int
    cross_border: bool
    safeguards: list[str]
    minimization_applied: bool


_VALID_BASES = {"legitimate_interest", "consent", "contract", "legal_obligation",
                "vital_interest", "public_task"}


def build_dpa_record(activity: str, lawful_basis: str, data_categories: list[str],
                     retention_days: int, cross_border: bool = False) -> DpaRecord:
    """Build an Article-30 record of processing. Validates lawful basis and
    flags safeguards required for cross-border transfers."""
    if lawful_basis not in _VALID_BASES:
        raise ValueError(f"invalid GDPR lawful basis {lawful_basis}")
    safeguards: list[str] = []
    if cross_border:
        safeguards = ["standard_contractual_clauses", "transfer_impact_assessment"]
    # Minimization: SpoofVane stores hashed fingerprints / redacted secrets only.
    minimization = all("raw_" not in c for c in data_categories)
    return DpaRecord(
        processing_activity=activity, lawful_basis=lawful_basis,
        data_categories=sorted(data_categories), retention_days=retention_days,
        cross_border=cross_border, safeguards=safeguards,
        minimization_applied=minimization,
    )
