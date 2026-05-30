"""v07 D2 — per-family calibrators.

The global Platt calibrator (calibration.py) maps a raw composite to a probability
with one curve for all candidates. But different kit families have different
base rates and score distributions — a crypto kit at raw 0.6 is more likely
malicious than an M365 kit at raw 0.6. D2 adds a per-family calibrator registry:
each family can have its OWN fitted Platt params, persisted separately, with a
graceful fallback to the global default when a family-specific fit is absent.

This never breaks the global path: calibrate_for_family(family=None) is exactly
the global calibrator. A family with no persisted fit also falls back to global.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .calibration import (
    CalibratedScore, PlattCalibrator, calibrate, load_calibrator,
)

# Known kit families (mirrors scoring.family). Unknown families fall back.
KNOWN_FAMILIES = ("m365", "banking", "payment", "crypto", "generic")


def _family_dir() -> Path:
    base = os.getenv("SPOOFVANE_CALIBRATION_PATH")
    if base:
        return Path(base).resolve().parent / "families"
    return (Path(__file__).resolve().parents[2] / "data" / "calibration" / "families")


def family_calibration_path(family: str) -> Path:
    return _family_dir() / f"{family.lower()}.json"


def load_family_calibrator(family: str | None) -> PlattCalibrator:
    """Load a family-specific calibrator, or the global default if the family is
    None / unknown / has no persisted fit."""
    if not family:
        return load_calibrator()
    path = family_calibration_path(family)
    try:
        data = json.loads(path.read_text())
        return PlattCalibrator(a=float(data["a"]), b=float(data["b"]))
    except (FileNotFoundError, KeyError, ValueError, OSError):
        # Graceful fallback to the global calibrator.
        return load_calibrator()


def save_family_calibrator(family: str, cal: PlattCalibrator, fitted_on: int,
                           path: Path | None = None) -> Path:
    """Persist a family-specific calibrator + provenance."""
    from datetime import datetime, timezone
    p = path or family_calibration_path(family)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "family": family, "a": cal.a, "b": cal.b, "fitted_on": fitted_on,
        "ts": datetime.now(timezone.utc).isoformat(),
    }, indent=2))
    return p


def calibrate_for_family(raw_score: float, contributions: dict[str, float],
                         family: str | None = None) -> CalibratedScore:
    """Calibrate using the family-specific curve when available, else global.
    family=None reproduces the global calibrate() exactly."""
    cal = load_family_calibrator(family)
    result = calibrate(raw_score, contributions, calibrator=cal)
    result.calibration = f"platt:{family}" if family else "platt"
    return result


def fit_family_calibrator(family: str,
                          samples: list[tuple[float, int]]) -> PlattCalibrator:
    """Fit a fresh Platt calibrator for a family from (raw_score, label) pairs."""
    cal = PlattCalibrator()
    cal.fit(samples)
    return cal
