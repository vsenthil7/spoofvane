"""DOM structural similarity score.

Combines two signals:
  1. Tag-frequency cosine similarity (cheap, robust to attribute shuffling)
  2. Form-target hint  (does the suspect have a login form?)

The combination gives a 0..1 score where 1.0 == structurally identical.
"""
from __future__ import annotations

import math
from collections import Counter

from bs4 import BeautifulSoup


def _tag_vector(html: bytes) -> Counter[str]:
    soup = BeautifulSoup(html, "lxml") if html else BeautifulSoup(b"", "lxml")
    return Counter(tag.name for tag in soup.find_all(True))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def _has_login_form(html: bytes) -> bool:
    if not html:
        return False
    soup = BeautifulSoup(html, "lxml")
    for form in soup.find_all("form"):
        inputs = form.find_all("input")
        names = {i.get("name", "").lower() for i in inputs}
        types = {i.get("type", "").lower() for i in inputs}
        if "password" in types or "password" in names:
            return True
    return False


def dom_score(canonical_html: bytes, suspect_html: bytes) -> float:
    """Return a structural similarity score in [0, 1]."""
    a = _tag_vector(canonical_html)
    b = _tag_vector(suspect_html)
    cosine = _cosine(a, b)

    # Bonus for matching login-form structure
    canonical_login = _has_login_form(canonical_html)
    suspect_login = _has_login_form(suspect_html)
    if canonical_login and suspect_login:
        cosine = min(1.0, cosine + 0.15)
    elif canonical_login != suspect_login:
        cosine = max(0.0, cosine - 0.15)

    return round(cosine, 4)
