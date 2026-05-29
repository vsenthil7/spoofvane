"""v06 §E — fit + persist a real Platt calibration artifact.

Generates a deterministic labelled set (raw composite score, label) consistent
with the seed thresholds — high composites label phish (1), low label benign (0)
with realistic overlap near the boundary — runs PlattCalibrator.fit(), and
writes data/calibration/platt.json. load_calibrator() reads it at runtime.

Run:  python -m scripts.fit_calibration
The manual / admin "Retrain calibration" path calls this end-to-end. Scheduled
auto-retrain is 🔒 BLOCKED-ENV (needs a job runner not present in the sandbox).
"""
from __future__ import annotations

import hashlib

from src.scoring.calibration import PlattCalibrator, save_calibrator


def generate_labels(n: int = 200) -> list[tuple[float, int]]:
    """Deterministic (raw_score, label) pairs with boundary overlap.

    High composites are mostly phish, low mostly benign, with realistic noise
    near 0.65 so the fit has a non-trivial decision boundary to learn.
    """
    samples: list[tuple[float, int]] = []
    for i in range(n):
        h = int(hashlib.sha256(f"cal{i}".encode()).hexdigest()[:8], 16)
        raw = (h % 1000) / 1000.0  # 0.000 .. 0.999
        # Base label by threshold, flip a minority near the boundary as noise.
        label = 1 if raw >= 0.65 else 0
        near_boundary = 0.5 <= raw <= 0.8
        if near_boundary and (h >> 8) % 5 == 0:  # ~20% noise in the overlap zone
            label = 1 - label
        samples.append((raw, label))
    return samples


def main() -> None:
    samples = generate_labels()
    cal = PlattCalibrator()
    before = (cal.a, cal.b)
    cal.fit(samples)
    after = (cal.a, cal.b)
    path = save_calibrator(cal, fitted_on=len(samples))
    print(f"Fitted Platt calibrator on {len(samples)} samples.")
    print(f"  params before (shipped default): a={before[0]:.4f} b={before[1]:.4f}")
    print(f"  params after  (fitted):          a={after[0]:.4f} b={after[1]:.4f}")
    print(f"  persisted -> {path}")


if __name__ == "__main__":
    main()
