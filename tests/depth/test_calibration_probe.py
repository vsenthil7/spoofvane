"""v06 §E Gate 5 — calibration depth probe.

Proves the calibrated probability comes from a PERSISTED FITTED model and is
input-dependent: two distinct raw scores map to two distinct calibrated
probabilities, and the fitted params differ from the shipped default (so we
know fit actually ran, not a no-op). Scheduled/auto-retrain is 🔒 BLOCKED-ENV.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.scoring.calibration import (
    PlattCalibrator, load_calibrator, save_calibrator, calibrate, calibration_path,
)


def test_persisted_artifact_exists_and_parses():
    path = calibration_path()
    assert path.exists(), f"no persisted calibration at {path}; run scripts.fit_calibration"
    data = json.loads(path.read_text())
    assert "a" in data and "b" in data and "fitted_on" in data
    assert data["fitted_on"] >= 4


def test_loaded_calibrator_differs_from_shipped_default():
    default = PlattCalibrator()
    loaded = load_calibrator()
    # Fit must have moved at least one parameter off the shipped default.
    assert (loaded.a, loaded.b) != (default.a, default.b), (
        "loaded calibrator equals the shipped default — fit did not run/persist"
    )


def test_calibrated_probability_is_input_dependent():
    cal = load_calibrator()
    low = calibrate(0.55, {"phash": 0.3, "dom": 0.25}, calibrator=cal).probability
    high = calibrate(0.85, {"phash": 0.5, "dom": 0.35}, calibrator=cal).probability
    assert low != high, "two distinct raw scores gave the same probability (constant)"
    assert high > low, "higher raw composite must map to higher phish probability"
    assert 0.0 <= low <= 1.0 and 0.0 <= high <= 1.0


def test_load_falls_back_to_default_when_absent(tmp_path, monkeypatch):
    """Negative: a missing artifact yields the shipped default, never a crash."""
    missing = tmp_path / "nope.json"
    monkeypatch.setenv("SPOOFVANE_CALIBRATION_PATH", str(missing))
    cal = load_calibrator()
    assert (cal.a, cal.b) == (PlattCalibrator().a, PlattCalibrator().b)


def test_composite_emits_contributions_and_probability(tmp_path, monkeypatch):
    """The scorer now emits score_contributions (sum ≈ composite) + probability."""
    from src.scoring.calibration import PlattCalibrator
    # Use a fitted calibrator written to a temp path.
    c = PlattCalibrator()
    c.fit([(0.9, 1), (0.85, 1), (0.1, 0), (0.2, 0), (0.95, 1), (0.05, 0)])
    p = tmp_path / "platt.json"
    save_calibrator(c, fitted_on=6, path=p)
    monkeypatch.setenv("SPOOFVANE_CALIBRATION_PATH", str(p))

    # Build a minimal Brand + InspectionResult and score with canonicals present.
    from src.common.models import Brand, InspectionResult
    brand = Brand(id="b1", name="Acme", login_url="https://acme.com/login", score_threshold=0.65)
    insp = InspectionResult(id="i1", suspect_url_id="s1", success=True, rendered_country="US")
    from src.scoring import composite as comp
    res = comp.score(
        brand,
        canonical_screenshot=b"PNGDATA", canonical_dom=b"<html><body></body></html>",
        canonical_logo=b"", canonical_favicon_md5=None, inspection=insp,
    )
    assert set(res.score_contributions) >= {"phash", "dom", "logo", "favicon"}
    assert res.probability is not None and 0.0 <= res.probability <= 1.0
    # Contributions sum should be close to the composite (within rounding).
    assert abs(sum(res.score_contributions.values()) - res.composite_score) < 0.05
