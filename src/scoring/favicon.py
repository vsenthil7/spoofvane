"""Favicon exact-match check.

A phishing page that uses the brand's exact favicon is high-signal.
We compare MD5 hashes — anything else is over-engineering for a 16x16 PNG.
"""
from __future__ import annotations


def favicon_match(canonical_md5: str | None, suspect_md5: str | None) -> bool:
    if not canonical_md5 or not suspect_md5:
        return False
    return canonical_md5.lower() == suspect_md5.lower()
