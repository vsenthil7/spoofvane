"""v07 D1 — auxiliary cross-surface signal fusion.

The v07 width surfaces (W1 social, W2 app-store, W3 marketplace, W8 RTP beacon,
etc.) each emit a normalized 0..1 risk signal on their findings. D1 fuses any
present auxiliary signals into the composite score WITHOUT disturbing the
visual-only path: when no aux signals are supplied, the composite is exactly the
visual blend as before (backward compatible). When aux signals ARE supplied,
they participate in the same renormalized weighting, so a strong social-clone or
beacon signal can raise a verdict even when visual similarity is moderate.

Default aux weights (brand/family-tunable later in D2):
    social_clone, app_clone, listing_nlp, beacon  -> 0.15 each (capped share).
Aux signals are clamped to [0,1]; unknown keys are ignored.
"""
from __future__ import annotations

from dataclasses import dataclass

# Recognized auxiliary signal keys and their default weights.
AUX_DEFAULT_WEIGHTS = {
    "social_clone": 0.15,
    "app_clone": 0.15,
    "listing_nlp": 0.15,
    "beacon": 0.20,        # a real-time foreign-origin beacon is a strong signal
}


@dataclass
class FusedScore:
    composite: float
    contributions: dict[str, float]
    aux_used: list[str]


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def fuse(
    visual_weights: dict[str, float],
    visual_values: dict[str, float],
    aux_signals: dict[str, float] | None = None,
    aux_weights: dict[str, float] | None = None,
) -> FusedScore:
    """Blend visual signals + optional auxiliary signals into one composite.

    visual_weights / visual_values: the existing phash/dom/logo/favicon maps
    (weights already zeroed for missing canonicals).
    aux_signals: optional {social_clone, app_clone, listing_nlp, beacon} in 0..1.

    Returns the renormalized composite + per-signal contributions. With no aux
    signals, the result equals the pure visual blend.
    """
    aux_signals = aux_signals or {}
    aux_w_table = aux_weights or AUX_DEFAULT_WEIGHTS

    # Effective weights: visual (as given) + aux (only for present, recognized keys).
    weights: dict[str, float] = dict(visual_weights)
    values: dict[str, float] = dict(visual_values)
    aux_used: list[str] = []
    for key, raw in aux_signals.items():
        if key not in aux_w_table:
            continue  # ignore unknown aux keys
        w = aux_w_table[key]
        if w <= 0:
            continue
        weights[key] = w
        values[key] = _clamp(raw)
        aux_used.append(key)

    total_w = sum(weights.values())
    if total_w == 0:
        return FusedScore(0.0, {k: 0.0 for k in weights}, [])

    composite = sum(weights[k] * values.get(k, 0.0) for k in weights) / total_w
    composite = round(min(1.0, float(composite)), 4)
    contributions = {
        k: round(weights[k] * values.get(k, 0.0) / total_w, 4) for k in weights
    }
    return FusedScore(composite=composite, contributions=contributions,
                      aux_used=sorted(aux_used))
