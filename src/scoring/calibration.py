"""C1 — calibrated probability + per-signal contribution (review C1).

Wraps the raw composite weighted sum in a Platt-scaling sigmoid so the output is
a *calibrated probability* (not a raw weighted sum), and emits the per-signal
contribution breakdown the spec requires. The Platt parameters are fitted from
labelled feedback (active-learning loop, D8/E6); a sensible default is shipped so
the calibrator is never a no-op.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path


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


# v06 §E — persisted fitted-model artifact. scripts/fit_calibration.py writes
# this; load_calibrator() reads it at runtime, falling back to the shipped
# default (never a no-op) when absent.
_DEFAULT_CALIBRATION_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "calibration" / "platt.json"
)


def calibration_path() -> Path:
    return Path(os.getenv("SPOOFVANE_CALIBRATION_PATH", str(_DEFAULT_CALIBRATION_PATH)))


def load_calibrator() -> PlattCalibrator:
    """Load the persisted Platt params, or the shipped default if absent."""
    path = calibration_path()
    try:
        data = json.loads(path.read_text())
        return PlattCalibrator(a=float(data["a"]), b=float(data["b"]))
    except (FileNotFoundError, KeyError, ValueError, OSError):
        return PlattCalibrator()


def save_calibrator(cal: PlattCalibrator, fitted_on: int, path: Path | None = None) -> Path:
    """Persist fitted Platt params + provenance to JSON."""
    from datetime import datetime, timezone
    p = path or calibration_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "a": cal.a, "b": cal.b, "fitted_on": fitted_on,
        "ts": datetime.now(timezone.utc).isoformat(),
    }, indent=2))
    return p
