"""Podcast RSS + video transcript ingestion for exec mentions.

Surfaces where an exec's voice/likeness is publicly available — the raw
material for voice-clone deepfakes. Input-dependent fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import ExecInput, OsintMode, get_osint_mode


@dataclass
class TranscriptHit:
    source: str
    title: str
    url: str
    minutes_of_audio: int
    voice_clone_risk: float


@dataclass
class TranscriptResult:
    exec_name: str
    hits: list[TranscriptHit] = field(default_factory=list)
    total_public_audio_minutes: int = 0


class TranscriptsSource:
    name = "transcripts"

    def search(self, exec_in: ExecInput) -> TranscriptResult:
        if get_osint_mode() == OsintMode.LIVE:
            return self._live(exec_in)
        return self._replay(exec_in)

    def _live(self, exec_in: ExecInput) -> TranscriptResult:  # pragma: no cover - BLOCKED-ENV
        raise NotImplementedError(
            "live podcast/YouTube transcript ingest is fixture-backed (BLOCKED-ENV)")

    def _replay(self, exec_in: ExecInput) -> TranscriptResult:
        s = exec_in.seed("transcripts")
        n = s % 4  # 0..3 hits — some execs have no public audio
        hits: list[TranscriptHit] = []
        total = 0
        for i in range(n):
            si = exec_in.seed("transcripts", str(i))
            mins = 12 + (si % 80)
            total += mins
            # More public audio -> higher voice-clone feasibility.
            risk = min(1.0, 0.2 + mins / 120)
            hits.append(TranscriptHit(
                source=["podcast", "youtube", "conference"][si % 3],
                title=f"{exec_in.name} on {['strategy','culture','the future'][si % 3]}",
                url=f"https://media-{si % 9999}.example/{exec_in.company.lower()}",
                minutes_of_audio=mins,
                voice_clone_risk=round(risk, 3),
            ))
        return TranscriptResult(
            exec_name=exec_in.name, hits=hits, total_public_audio_minutes=total,
        )
