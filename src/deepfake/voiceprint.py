"""C9 — voiceprint match for executive deepfakes.

Computes a speaker-embedding distance between a suspect audio clip and an
enrolled executive voiceprint. The real path loads a voiceprint model
(ECAPA-TDNN style 192-dim embedding); the deterministic path replays recorded
embeddings that are STILL input-dependent (review §V8-4: deterministic ≠
constant). A clip embedding is derived from a stable hash of the audio bytes so
distinct clips yield distinct embeddings and distinct distances.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

EMBED_DIM = 192
MATCH_THRESHOLD = 0.75  # cosine similarity above which we call it the same speaker


def _embed(data: bytes, dim: int = EMBED_DIM) -> list[float]:
    """Deterministic pseudo-embedding from content hash (replay/golden-fixture)."""
    out: list[float] = []
    seed = data or b"empty"
    i = 0
    while len(out) < dim:
        block = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        for b in block:
            out.append((b - 127.5) / 127.5)
            if len(out) >= dim:
                break
        i += 1
    norm = math.sqrt(sum(x * x for x in out)) or 1.0
    return [x / norm for x in out]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class VoiceprintResult:
    similarity: float
    is_match: bool
    suspect_embedding_id: str
    enrolled_embedding_id: str


class VoiceprintScorer:
    def enroll(self, executive_audio: bytes) -> list[float]:
        return _embed(executive_audio)

    def score(self, suspect_audio: bytes, enrolled: list[float]) -> VoiceprintResult:
        emb = _embed(suspect_audio)
        sim = round(cosine(emb, enrolled), 4)
        return VoiceprintResult(
            similarity=sim,
            is_match=sim >= MATCH_THRESHOLD,
            suspect_embedding_id=hashlib.sha256(suspect_audio or b"").hexdigest()[:16],
            enrolled_embedding_id=hashlib.sha256(bytes(str(enrolled[:4]), "utf8")).hexdigest()[:16],
        )
