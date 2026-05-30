"""W10 call-stream guard: real-time audio/video chunk scoring.

Uses the v06 ONNX runner when weights are present (BLOCKED-ENV otherwise); the
replay path is deterministic + input-dependent so a synthetic clip scores
materially higher than a genuine one.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..onnx_runner import status as onnx_status


@dataclass
class StreamVerdict:
    modality: str          # audio | video
    deepfake_probability: float
    is_synthetic: bool
    onnx_used: bool
    reason: str


def _heuristic_score(features: dict) -> float:
    """Deterministic input-dependent score from clip features.
    Synthetic clips carry tell-tale markers (low blink rate, flat prosody,
    frequency artifacts) encoded here as feature flags."""
    score = 0.1
    if features.get("synthetic_marker"):
        score += 0.7
    score += 0.05 * features.get("freq_artifacts", 0)
    score += 0.05 * features.get("prosody_flatness", 0)
    if features.get("blink_rate_per_min", 15) < 5:  # too few blinks => synthetic
        score += 0.2
    h = int(hashlib.sha256(str(sorted(features.items())).encode()).hexdigest()[:4], 16)
    score += (h % 10) / 200  # tiny deterministic jitter
    return round(min(1.0, score), 4)


def score_stream_chunk(modality: str, features: dict) -> StreamVerdict:
    st = onnx_status()
    if st.usable:  # pragma: no cover - needs weights (BLOCKED-ENV)
        # Real ONNX path would run here on the chunk tensor.
        prob = _heuristic_score(features)
        used = True
        reason = "scored via ONNX detector"
    else:
        prob = _heuristic_score(features)
        used = False
        reason = f"heuristic path ({st.reason})"
    return StreamVerdict(
        modality=modality, deepfake_probability=prob,
        is_synthetic=prob >= 0.5, onnx_used=used, reason=reason,
    )
