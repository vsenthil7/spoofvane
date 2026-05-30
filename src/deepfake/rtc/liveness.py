"""W10 liveness: challenge-response liveness for real-time calls."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LivenessResult:
    passed: bool
    confidence: float
    signals: list[str]


def liveness_check(signals: dict) -> LivenessResult:
    """Aggregate liveness signals (head-turn response, blink, micro-expressions,
    audio-video sync). A genuine live participant passes; a replayed/synthetic
    feed fails."""
    checks = {
        "challenge_response": signals.get("responded_to_challenge", False),
        "natural_blink": signals.get("blink_rate_per_min", 0) >= 8,
        "av_sync": signals.get("av_sync_ms", 999) <= 120,
        "micro_expression": signals.get("micro_expression_var", 0.0) >= 0.3,
    }
    passed_signals = [k for k, v in checks.items() if v]
    confidence = round(len(passed_signals) / len(checks), 4)
    return LivenessResult(
        passed=confidence >= 0.5,
        confidence=confidence,
        signals=passed_signals,
    )
