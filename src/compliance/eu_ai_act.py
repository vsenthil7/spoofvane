"""W14 EU AI Act risk classification of an AI system/use-case."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EuAiActClass(str, Enum):
    PROHIBITED = "prohibited"
    HIGH_RISK = "high_risk"
    LIMITED_RISK = "limited_risk"      # transparency obligations
    MINIMAL_RISK = "minimal_risk"


@dataclass
class EuAiActAssessment:
    use_case: str
    risk_class: EuAiActClass
    obligations: list[str]
    rationale: str


# Triggers (simplified, illustrative — not legal advice).
_PROHIBITED = {"social_scoring", "biometric_categorization_sensitive", "subliminal_manipulation"}
_HIGH_RISK = {"biometric_identification", "critical_infrastructure", "law_enforcement_profiling"}


def classify_ai_system(use_case: str, *, affects_individuals: bool = False,
                       automated_decisions: bool = False,
                       generates_content: bool = False) -> EuAiActAssessment:
    """Classify a use-case under the EU AI Act risk tiers."""
    uc = use_case.lower()
    if uc in _PROHIBITED:
        return EuAiActAssessment(
            use_case, EuAiActClass.PROHIBITED,
            ["cease deployment"], "use-case is in the Article 5 prohibited set")
    if uc in _HIGH_RISK or (affects_individuals and automated_decisions):
        return EuAiActAssessment(
            use_case, EuAiActClass.HIGH_RISK,
            ["risk_management_system", "data_governance", "technical_documentation",
             "human_oversight", "accuracy_robustness_logging"],
            "high-risk: automated decisions affecting individuals / Annex III area")
    if generates_content:
        return EuAiActAssessment(
            use_case, EuAiActClass.LIMITED_RISK,
            ["transparency_disclosure", "ai_generated_marking"],
            "limited-risk: content generation triggers transparency obligations")
    return EuAiActAssessment(
        use_case, EuAiActClass.MINIMAL_RISK, [],
        "minimal-risk: no Annex III / Article 5 triggers")
