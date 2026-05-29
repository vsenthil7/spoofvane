"""Redaction recommender: takes an exec dossier, flags PII to remove, returns a
ranked redaction list.

Aggregates the other OSINT sources into a single dossier, then ranks each
exposed item by removal priority (doxxing-grade PII first). The differential
probe requires two distinct execs to yield two distinct recommendation sets.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import ExecInput
from .data_broker import DataBrokerSource
from .linkedin_public import LinkedInPublicSource
from .transcripts import TranscriptsSource

# Removal priority weights — higher = redact first.
_PRIORITY = {
    "home_address": 1.0, "phone": 0.9, "relatives": 0.8, "prior_addresses": 0.75,
    "property_records": 0.7, "email": 0.6, "age": 0.4, "political_affiliation": 0.5,
    "public_audio": 0.65, "profile_photo": 0.55, "public_posts": 0.45,
}


@dataclass
class RedactionItem:
    item: str
    source: str
    priority: float
    rationale: str


@dataclass
class RedactionPlan:
    exec_name: str
    items: list[RedactionItem] = field(default_factory=list)
    overall_exposure: float = 0.0

    @property
    def ranked_items(self) -> list[str]:
        return [i.item for i in self.items]


class RedactionRecommender:
    name = "redaction"

    def __init__(self) -> None:
        self.broker = DataBrokerSource()
        self.linkedin = LinkedInPublicSource()
        self.transcripts = TranscriptsSource()

    def recommend(self, exec_in: ExecInput) -> RedactionPlan:
        broker = self.broker.check(exec_in)
        profile = self.linkedin.enrich(exec_in)
        audio = self.transcripts.search(exec_in)

        items: list[RedactionItem] = []
        for field_name in broker.all_exposed_fields:
            items.append(RedactionItem(
                item=field_name, source="data_broker",
                priority=_PRIORITY.get(field_name, 0.3),
                rationale=f"Listed by data brokers; {field_name} enables doxxing/social-eng.",
            ))
        if audio.total_public_audio_minutes > 30:
            items.append(RedactionItem(
                item="public_audio", source="transcripts",
                priority=_PRIORITY["public_audio"],
                rationale=f"{audio.total_public_audio_minutes} min public audio — voice-clone risk.",
            ))
        if profile.profile_photo_present:
            items.append(RedactionItem(
                item="profile_photo", source="linkedin_public",
                priority=_PRIORITY["profile_photo"],
                rationale="Public profile photo feeds face-swap deepfakes.",
            ))
        if profile.recent_public_posts:
            items.append(RedactionItem(
                item="public_posts", source="linkedin_public",
                priority=_PRIORITY["public_posts"],
                rationale="Public posts leak routine/voice for spear-phishing pretexts.",
            ))

        items.sort(key=lambda i: i.priority, reverse=True)
        overall = round(
            min(1.0, 0.5 * broker.exposure_score + 0.3 * profile.impersonation_risk
                + 0.2 * min(1.0, audio.total_public_audio_minutes / 120)),
            3,
        )
        return RedactionPlan(exec_name=exec_in.name, items=items, overall_exposure=overall)
