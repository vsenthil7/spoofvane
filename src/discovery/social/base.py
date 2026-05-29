"""W1 social engine — finding model, handle similarity, profile-clone scoring,
and the per-platform adapter base.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

# Platforms covered (mirrors ZeroFox/Doppel multi-channel breadth).
PLATFORMS = (
    "x_twitter", "facebook", "instagram", "linkedin", "tiktok",
    "youtube", "telegram_public", "reddit", "threads", "discord_invite",
)

# Homoglyph confusables: visually-similar substitutions attackers use in handles.
_HOMOGLYPHS = {
    "o": "0", "l": "1", "i": "1", "e": "3", "a": "@", "s": "5", "g": "9", "b": "6",
}


@dataclass
class SocialFinding:
    platform: str
    handle: str
    url: str
    avatar_hash: str
    bio: str
    follower_count: int
    created_at: str
    verified: bool = False
    clone_score: float = 0.0
    handle_risk: float = 0.0

    @property
    def social_clone_signal(self) -> float:
        """Combined signal fed into composite.score() as `social_clone`."""
        return round(min(1.0, 0.6 * self.clone_score + 0.4 * self.handle_risk), 4)


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def handle_similarity(brand_handle: str, candidate: str) -> float:
    """Risk in [0,1] that `candidate` impersonates `brand_handle`.

    Combines normalized edit-distance with a homoglyph-deconfusion check
    (de-confused candidate matching the brand scores very high).
    """
    a = brand_handle.lower().lstrip("@")
    b = candidate.lower().lstrip("@")
    if not a or not b:
        return 0.0
    # De-confuse the candidate (map confusables back to letters) and compare.
    inv = {v: k for k, v in _HOMOGLYPHS.items()}
    deconfused = "".join(inv.get(ch, ch) for ch in b)
    edit = _levenshtein(a, b)
    edit_norm = 1.0 - edit / max(len(a), len(b))
    homoglyph_hit = 1.0 if (deconfused == a and b != a) else 0.0
    # Exact handle is NOT impersonation risk (it's the brand itself) -> 0.
    if b == a:
        return 0.0
    return round(min(1.0, max(edit_norm, homoglyph_hit) if (edit_norm > 0.6 or homoglyph_hit) else edit_norm * 0.5), 4)


def profile_clone_score(brand_logo_hash: str, avatar_hash: str) -> float:
    """Avatar-vs-brand-logo similarity in [0,1].

    Reuses the perceptual-distance idea from scoring.logo_embedding: closer
    hashes => higher clone score. Deterministic and input-dependent.
    """
    if not brand_logo_hash or not avatar_hash:
        return 0.0
    if brand_logo_hash == avatar_hash:
        return 1.0
    # Hamming-like distance over the hex digests, normalized.
    n = min(len(brand_logo_hash), len(avatar_hash))
    if n == 0:
        return 0.0
    same = sum(1 for i in range(n) if brand_logo_hash[i] == avatar_hash[i])
    return round(same / n, 4)


class SocialAdapter:
    """Per-platform adapter. Concrete behaviour is data-driven by platform name
    but each produces input-dependent findings (distinct brands -> distinct
    findings) and respects live/replay/mock mode.
    """

    def __init__(self, platform: str) -> None:
        if platform not in PLATFORMS:
            raise ValueError(f"unknown platform {platform}")
        self.platform = platform

    def _mode(self) -> str:
        return os.getenv("SPOOFVANE_BD_MODE", "replay").lower()

    def search(self, brand_name: str, brand_handle: str, brand_logo_hash: str) -> list[SocialFinding]:
        if self._mode() == "live":  # pragma: no cover - BLOCKED-ENV
            raise NotImplementedError(
                f"live {self.platform} search needs platform API keys (BLOCKED-ENV)")
        return self._replay(brand_name, brand_handle, brand_logo_hash)

    def _replay(self, brand_name: str, brand_handle: str, brand_logo_hash: str) -> list[SocialFinding]:
        base = int(hashlib.sha256(f"{self.platform}|{brand_name}".encode()).hexdigest()[:8], 16)
        n = base % 3  # 0..2 impersonators per platform, varies by brand
        out: list[SocialFinding] = []
        slug = brand_name.lower().replace(" ", "")
        for i in range(n):
            s = int(hashlib.sha256(f"{self.platform}|{brand_name}|{i}".encode()).hexdigest()[:8], 16)
            # Construct a plausible impersonator handle (homoglyph or suffix).
            if s % 2 == 0:
                handle = "@" + slug.replace("o", "0").replace("i", "1")  # homoglyph
            else:
                handle = f"@{slug}_official{s % 99}"
            # Avatar hash: near-clone when s%3==0 else unrelated.
            if s % 3 == 0:
                avatar = brand_logo_hash  # exact clone
            else:
                avatar = hashlib.sha256(f"avatar{s}".encode()).hexdigest()
            clone = profile_clone_score(brand_logo_hash, avatar)
            hrisk = handle_similarity(brand_handle, handle)
            out.append(SocialFinding(
                platform=self.platform,
                handle=handle,
                url=f"https://{self.platform}.example/{handle.lstrip('@')}",
                avatar_hash=avatar,
                bio=f"Official {brand_name} support — DM for help",
                follower_count=s % 50000,
                created_at=f"2026-0{1 + (s % 5)}-{1 + (s % 27):02d}",
                verified=False,
                clone_score=clone,
                handle_risk=hrisk,
            ))
        return out
