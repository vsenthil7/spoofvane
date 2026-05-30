"""v07 W10 Gate — deepfake RTC guard differential probe.

A synthetic voice/video clip vs a genuine clip => distinct deepfake
probabilities; liveness passes for a live participant, fails for a replay;
C2PA provenance present vs absent vs tampered. Model weights / live RTC are
🔒 BLOCKED-ENV; replay fixtures are deterministic + input-dependent.
"""
from __future__ import annotations

from src.deepfake.rtc.call_stream_guard import score_stream_chunk
from src.deepfake.rtc.liveness import liveness_check
from src.deepfake.rtc.provenance_c2pa import verify_c2pa


def test_synthetic_vs_genuine_distinct_probability():
    synthetic = score_stream_chunk("audio", {
        "synthetic_marker": True, "freq_artifacts": 4, "prosody_flatness": 5,
        "blink_rate_per_min": 2,
    })
    genuine = score_stream_chunk("audio", {
        "synthetic_marker": False, "freq_artifacts": 0, "prosody_flatness": 0,
        "blink_rate_per_min": 16,
    })
    assert synthetic.deepfake_probability > genuine.deepfake_probability
    assert synthetic.is_synthetic is True
    assert genuine.is_synthetic is False


def test_onnx_blocked_env_uses_heuristic():
    v = score_stream_chunk("video", {"synthetic_marker": True})
    # Without weights, onnx_used is False and reason notes BLOCKED-ENV heuristic.
    assert v.onnx_used is False
    assert "heuristic" in v.reason.lower()


def test_liveness_live_vs_replay():
    live = liveness_check({
        "responded_to_challenge": True, "blink_rate_per_min": 15,
        "av_sync_ms": 40, "micro_expression_var": 0.6,
    })
    replay = liveness_check({
        "responded_to_challenge": False, "blink_rate_per_min": 1,
        "av_sync_ms": 800, "micro_expression_var": 0.0,
    })
    assert live.passed is True and replay.passed is False
    assert live.confidence > replay.confidence


def test_c2pa_present_valid_absent_tampered():
    trusted = verify_c2pa({"signature_valid": True, "issuer": "Truepic", "ai_generated": False})
    tampered = verify_c2pa({"signature_valid": False, "issuer": "x"})
    absent = verify_c2pa(None)
    assert trusted.provenance_present is True and trusted.trust == "trusted"
    assert tampered.trust == "tampered" and tampered.provenance_present is False
    assert absent.trust == "unverified" and absent.has_manifest is False


def test_ai_generated_declaration_surfaced():
    r = verify_c2pa({"signature_valid": True, "issuer": "OpenAI", "ai_generated": True})
    assert r.ai_generated_declared is True
