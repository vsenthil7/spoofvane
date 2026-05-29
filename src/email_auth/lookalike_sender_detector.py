"""W11 lookalike-sender detector: cousin-domain sending detection.

Flags sending domains that are confusable with the protected domain
(homoglyph, typo, TLD-swap, subdomain-stuffing). Reuses the homoglyph idea
from discovery/social.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_HOMOGLYPHS = {"o": "0", "l": "1", "i": "1", "e": "3", "a": "@", "s": "5"}


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


@dataclass
class LookalikeSender:
    sender_domain: str
    technique: str   # homoglyph | typo | tld_swap | subdomain_stuff
    risk: float


def detect_lookalike_senders(protected_domain: str, sender_domains: list[str]) -> list[LookalikeSender]:
    out: list[LookalikeSender] = []
    pd = protected_domain.lower()
    pd_name = pd.split(".")[0]
    for s in sender_domains:
        sd = s.lower()
        if sd == pd:
            continue  # the real domain
        sd_name = sd.split(".")[0]
        # TLD swap: same name, different TLD.
        if sd_name == pd_name and sd != pd:
            out.append(LookalikeSender(s, "tld_swap", 0.85))
            continue
        # Subdomain stuffing: protected name appears as a subdomain label.
        if pd_name in sd.split(".")[:-2] or (pd in sd and not sd.endswith(pd)):
            out.append(LookalikeSender(s, "subdomain_stuff", 0.8))
            continue
        # Homoglyph: de-confused name matches.
        inv = {v: k for k, v in _HOMOGLYPHS.items()}
        deconfused = "".join(inv.get(ch, ch) for ch in sd_name)
        if deconfused == pd_name and sd_name != pd_name:
            out.append(LookalikeSender(s, "homoglyph", 0.9))
            continue
        # Typo: small edit distance to the protected name.
        dist = _levenshtein(pd_name, sd_name)
        if 0 < dist <= 2:
            out.append(LookalikeSender(s, "typo", round(0.9 - 0.2 * (dist - 1), 4)))
    out.sort(key=lambda x: x.risk, reverse=True)
    return out
