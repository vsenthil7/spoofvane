"""D6 — multimodal verdict: fuse text + image + audio for a deepfake verdict.

Combines the C10 deepfake score (video/image+audio), the C9 voiceprint result,
and an LLM text-context signal into a single structured verdict with rationale.
Deterministic under replay; the text signal in live mode would be a Claude call.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .deepfake_score import DeepfakeResult
from .voiceprint import VoiceprintResult


@dataclass
class MultimodalVerdict:
    verdict: str  # "deepfake" | "suspicious" | "authentic"
    confidence: float
    modalities_used: list[str] = field(default_factory=list)
    rationale: str = ""
    signals: dict[str, float] = field(default_factory=dict)


def fuse(deepfake: DeepfakeResult, voiceprint: VoiceprintResult | None = None,
         text_context_risk: float = 0.0) -> MultimodalVerdict:
    modalities = ["image", "audio"]
    signals = {
        "deepfake_prob": deepfake.probability,
        "voice_mismatch": round(1.0 - voiceprint.similarity, 4) if voiceprint else 0.0,
        "text_context_risk": round(text_context_risk, 4),
    }
    if voiceprint:
        modalities.append("voice")
    if text_context_risk:
        modalities.append("text")

    # voice MISMATCH (low similarity to enrolled exec) raises suspicion
    voice_term = signals["voice_mismatch"] if voiceprint else 0.0
    fused = round(0.5 * deepfake.probability + 0.3 * voice_term + 0.2 * text_context_risk, 4)

    if fused >= 0.6:
        verdict, rationale = "deepfake", "High multimodal deepfake signal across modalities."
    elif fused >= 0.35:
        verdict, rationale = "suspicious", "Mixed signals; route to human deepfake review."
    else:
        verdict, rationale = "authentic", "Signals consistent with authentic media."

    return MultimodalVerdict(
        verdict=verdict, confidence=fused, modalities_used=modalities,
        rationale=rationale, signals=signals,
    )
