"""v07 D1 Gate — cross-surface signal fusion differential probe.

With no aux signals, fuse() == the pure visual blend (backward compatible). A
strong auxiliary signal (beacon/social-clone) raises the composite vs none.
Unknown aux keys are ignored; aux values are clamped to [0,1].
"""
from __future__ import annotations

from src.scoring.signal_fusion import fuse, AUX_DEFAULT_WEIGHTS


_VIS_W = {"phash": 0.4, "dom": 0.3, "logo": 0.2, "favicon": 0.1}
_VIS_V = {"phash": 0.5, "dom": 0.5, "logo": 0.5, "favicon": 0.0}


def _pure_visual(weights, values):
    tw = sum(weights.values())
    return round(sum(weights[k] * values[k] for k in weights) / tw, 4)


def test_no_aux_equals_pure_visual_blend():
    fused = fuse(_VIS_W, _VIS_V, aux_signals=None)
    assert fused.composite == _pure_visual(_VIS_W, _VIS_V)
    assert fused.aux_used == []
    # Contributions still sum (approximately) to the composite.
    assert abs(sum(fused.contributions.values()) - fused.composite) < 1e-6


def test_empty_aux_dict_equals_pure_visual():
    fused = fuse(_VIS_W, _VIS_V, aux_signals={})
    assert fused.composite == _pure_visual(_VIS_W, _VIS_V)


def test_strong_aux_raises_composite():
    base = fuse(_VIS_W, _VIS_V).composite
    with_beacon = fuse(_VIS_W, _VIS_V, aux_signals={"beacon": 1.0}).composite
    # A maximal beacon signal pulls the composite up vs the visual-only blend
    # (visual values are all 0.5, beacon is 1.0 -> blend rises).
    assert with_beacon > base


def test_strong_aux_lowers_when_visual_high():
    high_vis = {"phash": 1.0, "dom": 1.0, "logo": 1.0, "favicon": 1.0}
    base = fuse(_VIS_W, high_vis).composite
    with_low_aux = fuse(_VIS_W, high_vis, aux_signals={"social_clone": 0.0}).composite
    # A zero social signal drags a fully-similar visual blend down somewhat.
    assert with_low_aux < base


def test_unknown_aux_key_ignored():
    a = fuse(_VIS_W, _VIS_V, aux_signals={"not_a_signal": 1.0})
    b = fuse(_VIS_W, _VIS_V)
    assert a.composite == b.composite
    assert a.aux_used == []


def test_aux_clamped_to_unit_interval():
    over = fuse(_VIS_W, _VIS_V, aux_signals={"beacon": 5.0})
    one = fuse(_VIS_W, _VIS_V, aux_signals={"beacon": 1.0})
    assert over.composite == one.composite  # 5.0 clamped to 1.0
    neg = fuse(_VIS_W, _VIS_V, aux_signals={"beacon": -3.0})
    zero = fuse(_VIS_W, _VIS_V, aux_signals={"beacon": 0.0})
    assert neg.composite == zero.composite


def test_multiple_aux_signals_all_used():
    fused = fuse(_VIS_W, _VIS_V, aux_signals={
        "social_clone": 0.8, "app_clone": 0.7, "listing_nlp": 0.6, "beacon": 0.9,
    })
    assert fused.aux_used == ["app_clone", "beacon", "listing_nlp", "social_clone"]
    assert set(AUX_DEFAULT_WEIGHTS) >= set(fused.aux_used)
