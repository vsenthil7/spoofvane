"""v07 W10 — Deepfake real-time communication guard (builds on v06 ONNX runner).

Reality Defender multimodal real-time parity. Scores live audio/video call
streams for synthetic content, checks liveness, and verifies C2PA content
provenance. Model weights / live RTC are 🔒 BLOCKED-ENV; replay ships
deterministic input-dependent fixtures (a synthetic clip scores higher than a
genuine one).
"""
from __future__ import annotations

from .call_stream_guard import score_stream_chunk, StreamVerdict
from .liveness import liveness_check, LivenessResult
from .provenance_c2pa import verify_c2pa, C2paResult

__all__ = [
    "score_stream_chunk", "StreamVerdict",
    "liveness_check", "LivenessResult",
    "verify_c2pa", "C2paResult",
]
