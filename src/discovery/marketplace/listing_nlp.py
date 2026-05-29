"""W3 listing NLP: counterfeit-language classifier.

Lexicon + heuristic classifier that scores how strongly a listing's text
signals a counterfeit/rogue listing. Differential by construction: a listing
saying "genuine OEM replica $5" scores high; an authorized-reseller listing
scores low. Deterministic, no model download (rule-based, explainable).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Phrases strongly associated with counterfeit / grey-market listings.
_COUNTERFEIT_PHRASES = [
    "replica", "1:1", "aaa quality", "oem no box", "unauthorized",
    "factory direct no warranty", "mirror copy", "super clone", "boxless",
    "100% genuine replica", "high imitation", "knock off", "knockoff",
    "inspired by", "compatible with original",
]
# Phrases an authorized reseller uses (negative signal).
_AUTHORIZED_PHRASES = [
    "authorized reseller", "official store", "manufacturer warranty",
    "brand authorized", "ships from brand", "with full warranty",
]


@dataclass
class CounterfeitSignals:
    counterfeit_hits: list[str]
    authorized_hits: list[str]
    score: float


def counterfeit_language_score(title: str, description: str = "") -> CounterfeitSignals:
    text = f"{title} {description}".lower()
    cf = [p for p in _COUNTERFEIT_PHRASES if p in text]
    auth = [p for p in _AUTHORIZED_PHRASES if p in text]
    # Contradiction ("genuine" + "replica") is itself a strong counterfeit tell.
    contradiction = ("genuine" in text or "authentic" in text) and bool(cf)
    raw = 0.25 * len(cf) + (0.3 if contradiction else 0.0) - 0.3 * len(auth)
    score = max(0.0, min(1.0, raw))
    return CounterfeitSignals(counterfeit_hits=cf, authorized_hits=auth, score=round(score, 4))
