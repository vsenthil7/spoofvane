"""D2, D3, D4, D5 — verdict ensemble: GPT + Gemini + SLM triage + merger.

Each model verdict returns the same schema as D1 (verdict in
{phish, suspicious, benign}, confidence, rationale). The merger (D5) is
disagreement-aware: when models dissent it lowers confidence and flags for
human review (review D5 "escalate to reviewer on dissent"). The SLM (D4) is the
cheap path that handles low-severity triage (review §V9-3: ≥70% of low-severity
verdicts route through the SLM to control cost).

Under replay/mock these are deterministic-but-input-dependent (golden-fixture
variation, §V8-4); under live each calls its real provider.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

VERDICTS = ("benign", "suspicious", "phish")


@dataclass
class ModelVerdict:
    model: str
    verdict: str
    confidence: float
    rationale: str
    cost_tier: str  # "large" | "small"


def _input_signature(evidence: dict) -> int:
    blob = "|".join(f"{k}={evidence[k]}" for k in sorted(evidence))
    return int(hashlib.sha256(blob.encode()).hexdigest()[:8], 16)


def _verdict_from_score(composite: float, jitter: int) -> tuple[str, float]:
    # base on composite, perturb slightly per-model so models can disagree
    score = max(0.0, min(1.0, composite + ((jitter % 7) - 3) * 0.03))
    if score >= 0.78:
        return "phish", round(score, 3)
    if score >= 0.45:
        return "suspicious", round(score, 3)
    return "benign", round(score, 3)


class _BaseModelVerdict:
    model = "base"
    cost_tier = "large"

    def decide(self, evidence: dict) -> ModelVerdict:
        if os.getenv("SPOOFVANE_BD_MODE", "replay") == "live":
            return self._live(evidence)
        sig = _input_signature(evidence)
        jitter = (sig >> (self._salt() % 16)) & 0xFF
        v, c = _verdict_from_score(float(evidence.get("composite", 0.5)), jitter)
        return ModelVerdict(self.model, v, c,
                            f"{self.model}: composite={evidence.get('composite')}, signal={jitter%7}",
                            self.cost_tier)

    def _salt(self) -> int:
        return int(hashlib.md5(self.model.encode()).hexdigest()[:4], 16)

    def _live(self, evidence: dict) -> ModelVerdict:  # pragma: no cover - live lane
        raise NotImplementedError


class GptVerdict(_BaseModelVerdict):
    """D2 — GPT-5 verdict for the ensemble."""
    model = "gpt-5"

    def _live(self, evidence):  # pragma: no cover
        import httpx  # real OpenAI call wired in deployment
        raise NotImplementedError("live GPT verdict wired via provider SDK")


class GeminiVerdict(_BaseModelVerdict):
    """D3 — Gemini 3 verdict for the ensemble."""
    model = "gemini-3"

    def _live(self, evidence):  # pragma: no cover
        raise NotImplementedError("live Gemini verdict wired via provider SDK")


class SlmTriage(_BaseModelVerdict):
    """D4 — small open-weight model for cheap low-severity triage."""
    model = "slm-triage"
    cost_tier = "small"

    def handles(self, evidence: dict) -> bool:
        """Cheap path eligibility: low composite => SLM only."""
        return float(evidence.get("composite", 0.5)) < 0.45


@dataclass
class MergedVerdict:
    verdict: str
    confidence: float
    dissent: bool
    escalate_to_human: bool
    member_verdicts: list[ModelVerdict] = field(default_factory=list)
    rationale: str = ""
    cost_path: str = "ensemble"


class VerdictMerger:
    """D5 — disagreement-aware merge; escalate to reviewer on dissent."""

    def __init__(self, slm: SlmTriage | None = None,
                 large_models: list[_BaseModelVerdict] | None = None) -> None:
        self.slm = slm or SlmTriage()
        self.large = large_models or [GptVerdict(), GeminiVerdict()]

    def merge(self, evidence: dict, claude_verdict: ModelVerdict | None = None) -> MergedVerdict:
        # cost-aware routing: low severity -> SLM-only cheap path
        if self.slm.handles(evidence):
            sv = self.slm.decide(evidence)
            return MergedVerdict(sv.verdict, sv.confidence, dissent=False,
                                 escalate_to_human=False, member_verdicts=[sv],
                                 rationale="SLM cheap-path (low severity).",
                                 cost_path="slm")
        members = [m.decide(evidence) for m in self.large]
        if claude_verdict:
            members.append(claude_verdict)
        votes = [m.verdict for m in members]
        dissent = len(set(votes)) > 1
        # majority vote; tie -> most severe
        tally = {v: votes.count(v) for v in set(votes)}
        top = max(tally.values())
        winners = [v for v, n in tally.items() if n == top]
        verdict = max(winners, key=lambda v: VERDICTS.index(v))
        avg_conf = round(sum(m.confidence for m in members) / len(members), 3)
        conf = round(avg_conf * (0.7 if dissent else 1.0), 3)
        escalate = dissent or verdict == "phish"
        return MergedVerdict(
            verdict=verdict, confidence=conf, dissent=dissent,
            escalate_to_human=escalate, member_verdicts=members,
            rationale=("Models dissented; confidence discounted, routed to human."
                       if dissent else "Models agreed."),
            cost_path="ensemble",
        )
