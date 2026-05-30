"""v07 D2 Gate — per-family calibrator differential probe.

family=None reproduces the global calibrate() exactly; a fitted family-specific
calibrator yields a different probability than global at the same raw score; an
unknown/unfitted family falls back to global; fitting shifts params; save/load
round-trips. Uses a temp calibration path so the real data dir is untouched.
"""
from __future__ import annotations

import json

import pytest

from src.scoring.calibration import calibrate, PlattCalibrator
from src.scoring.family_calibration import (
    calibrate_for_family, load_family_calibrator, save_family_calibrator,
    fit_family_calibrator, family_calibration_path,
)

_CONTRIB = {"phash": 0.3, "dom": 0.2, "logo": 0.1, "favicon": 0.05}


@pytest.fixture
def temp_calib(tmp_path, monkeypatch):
    # Point the calibration path at a temp dir; families live under ./families.
    cal_file = tmp_path / "platt.json"
    monkeypatch.setenv("SPOOFVANE_CALIBRATION_PATH", str(cal_file))
    return tmp_path


def test_family_none_equals_global(temp_calib):
    raw = 0.7
    global_p = calibrate(raw, _CONTRIB).probability
    family_none_p = calibrate_for_family(raw, _CONTRIB, family=None).probability
    assert family_none_p == global_p


def test_unfitted_family_falls_back_to_global(temp_calib):
    raw = 0.7
    global_p = calibrate(raw, _CONTRIB).probability
    # No persisted crypto fit yet -> falls back to global curve.
    crypto_p = calibrate_for_family(raw, _CONTRIB, family="crypto").probability
    assert crypto_p == global_p


def test_fitted_family_differs_from_global(temp_calib):
    raw = 0.6
    global_p = calibrate(raw, _CONTRIB).probability
    # Fit a crypto calibrator on data where 0.6 is almost always malicious.
    samples = [(0.55, 1), (0.6, 1), (0.62, 1), (0.4, 0), (0.3, 0), (0.65, 1), (0.5, 1)]
    cal = fit_family_calibrator("crypto", samples)
    save_family_calibrator("crypto", cal, fitted_on=len(samples))
    crypto_p = calibrate_for_family(raw, _CONTRIB, family="crypto").probability
    assert crypto_p != global_p
    assert calibrate_for_family(raw, _CONTRIB, family="crypto").calibration == "platt:crypto"


def test_distinct_families_distinct_curves(temp_calib):
    # Two families fitted on different distributions yield different curves.
    crypto = fit_family_calibrator("crypto", [(0.6, 1), (0.62, 1), (0.58, 1), (0.3, 0), (0.4, 0)])
    m365 = fit_family_calibrator("m365", [(0.6, 0), (0.62, 0), (0.58, 0), (0.8, 1), (0.85, 1)])
    save_family_calibrator("crypto", crypto, fitted_on=5)
    save_family_calibrator("m365", m365, fitted_on=5)
    raw = 0.6
    crypto_p = calibrate_for_family(raw, _CONTRIB, family="crypto").probability
    m365_p = calibrate_for_family(raw, _CONTRIB, family="m365").probability
    # Same raw score, but the two family curves disagree (per-family calibration
    # is doing something) and each carries its own label.
    assert crypto_p != m365_p
    assert calibrate_for_family(raw, _CONTRIB, family="crypto").calibration == "platt:crypto"
    assert calibrate_for_family(raw, _CONTRIB, family="m365").calibration == "platt:m365"


def test_save_load_roundtrip(temp_calib):
    cal = PlattCalibrator(a=-7.1, b=4.4)
    path = save_family_calibrator("banking", cal, fitted_on=10)
    assert path.exists()
    loaded = load_family_calibrator("banking")
    assert round(loaded.a, 4) == -7.1
    assert round(loaded.b, 4) == 4.4
    data = json.loads(path.read_text())
    assert data["family"] == "banking" and data["fitted_on"] == 10


def test_fit_shifts_params(temp_calib):
    cal = fit_family_calibrator("payment", [(0.7, 1), (0.72, 1), (0.2, 0), (0.25, 0), (0.68, 1)])
    default = PlattCalibrator()
    assert (cal.a, cal.b) != (default.a, default.b)
