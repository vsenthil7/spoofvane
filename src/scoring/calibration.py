"""C1 — calibrated probability + per-signal contribution (review C1).

Wraps the raw composite weighted sum in a Platt-scaling sigmoid so the output is
a *calibrated probability* (not a raw weighted sum), and emits the per-signal
contribution breakdown the spec requires. The Platt parameters are fitted from
labelled feedback (active-learning loop, D8/E6); a sensible default is shipped so
the calibrator is never a no-op.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class CalibratedScore:
    probability: float
    raw_score: float
    contributions: dict[str, float]
    calibration: str = "platt"


@dataclass
class PlattCalibrator:
    # default params chosen so raw 0.65 (the legacy threshold) -> ~0.5 prob
    a: float = -6.5
    b: float = 4.225  # = -a * 0.65

    def probability(self, raw: float) -> float:
        z = self.a * raw + self.b
        # P(phish) increases with raw -> invert sign
        return 1.0 / (1.0 + math.exp(z))

    def fit(self, samples: list[tuple[float, int]]) -> None:
        """Newton-step Platt fit on (raw_score, label) pairs. Shifts calibration."""
        if len(samples) < 4:
            return
        a, b = self.a, self.b
        for _ in range(50):
            grad_a = grad_b = 0.0
            for raw, y in samples:
                p = 1.0 / (1.0 + math.exp(a * raw + b))
                grad_a += (p - y) * raw
                grad_b += (p - y)
            a -= 0.1 * grad_a / len(samples)
            b -= 0.1 * grad_b / len(samples)
        self.a, self.b = a, b


def calibrate(raw_score: float, contributions: dict[str, float],
              calibrator: PlattCalibrator | None = None) -> CalibratedScore:
    cal = calibrator or PlattCalibrator()
    return CalibratedScore(
        probability=round(cal.probability(raw_score), 4),
        raw_score=round(raw_score, 4),
        contributions={k: round(v, 4) for k, v in contributions.items()},
    )
