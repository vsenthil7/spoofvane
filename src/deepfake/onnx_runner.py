"""v06 §F.2 — Deepfake ONNX runner.

Real onnxruntime InferenceSession load path for image/audio/video detectors.
Feature-flagged via SPOOFVANE_DEEPFAKE_ONNX: when 0 (default) or weights are
absent, the runner is disabled and the existing heuristic deepfake_score path
is used — this is 🔒 BLOCKED-ENV (no model weights ship in the sandbox), never
reported as 0% "done". When enabled with weights present, it runs a genuine
session.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[2] / "data" / "models"


def onnx_enabled() -> bool:
    return os.getenv("SPOOFVANE_DEEPFAKE_ONNX", "0") == "1"


def models_dir() -> Path:
    return Path(os.getenv("SPOOFVANE_ONNX_DIR", str(_DEFAULT_MODELS_DIR)))


@dataclass
class OnnxStatus:
    enabled: bool
    runtime_available: bool
    weights_present: bool
    reason: str

    @property
    def usable(self) -> bool:
        return self.enabled and self.runtime_available and self.weights_present


def _runtime_available() -> bool:
    try:
        import onnxruntime  # noqa: F401
        return True
    except ImportError:
        return False


def status(model_name: str = "deepfake_image.onnx") -> OnnxStatus:
    enabled = onnx_enabled()
    rt = _runtime_available()
    weights = (models_dir() / model_name).exists()
    if not enabled:
        reason = "disabled (SPOOFVANE_DEEPFAKE_ONNX=0) — using heuristic path; BLOCKED-ENV"
    elif not rt:
        reason = "onnxruntime not installed — BLOCKED-ENV"
    elif not weights:
        reason = f"weights {model_name} absent in {models_dir()} — BLOCKED-ENV"
    else:
        reason = "ready"
    return OnnxStatus(enabled=enabled, runtime_available=rt, weights_present=weights, reason=reason)


class OnnxDeepfakeRunner:
    """Loads an ONNX detector and scores a tensor. Real session when usable."""

    def __init__(self, model_name: str = "deepfake_image.onnx") -> None:
        self.model_name = model_name
        self._session = None

    def _load(self):  # pragma: no cover - needs weights + runtime (BLOCKED-ENV)
        import numpy as np  # noqa: F401
        import onnxruntime as ort
        path = str(models_dir() / self.model_name)
        self._session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        return self._session

    def score(self, tensor) -> float:  # pragma: no cover - BLOCKED-ENV
        st = status(self.model_name)
        if not st.usable:
            raise RuntimeError(f"ONNX runner not usable: {st.reason}")
        sess = self._session or self._load()
        inp = sess.get_inputs()[0].name
        out = sess.run(None, {inp: tensor})
        return float(out[0].ravel()[0])
