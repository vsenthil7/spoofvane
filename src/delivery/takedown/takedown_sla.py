"""W6 SLA tracker: time-to-takedown across state transitions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


class SlaState(str, Enum):
    FILED = "filed"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


# Allowed forward transitions.
_TRANSITIONS = {
    SlaState.FILED: {SlaState.ACKNOWLEDGED, SlaState.REJECTED},
    SlaState.ACKNOWLEDGED: {SlaState.IN_PROGRESS, SlaState.REJECTED},
    SlaState.IN_PROGRESS: {SlaState.RESOLVED, SlaState.REJECTED},
    SlaState.RESOLVED: set(),
    SlaState.REJECTED: set(),
}


@dataclass
class SlaEvent:
    state: SlaState
    ts: datetime


@dataclass
class SlaTracker:
    state: SlaState = SlaState.FILED
    history: list[SlaEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.history:
            self.history.append(SlaEvent(self.state, datetime.now(timezone.utc)))

    def transition(self, to: SlaState, at: datetime | None = None) -> None:
        if to not in _TRANSITIONS[self.state]:
            raise ValueError(f"illegal SLA transition {self.state.value} -> {to.value}")
        self.state = to
        self.history.append(SlaEvent(to, at or datetime.now(timezone.utc)))

    def time_to_resolution(self) -> timedelta | None:
        """Elapsed FILED->RESOLVED, or None if not resolved."""
        filed = self.history[0].ts
        for ev in self.history:
            if ev.state == SlaState.RESOLVED:
                return ev.ts - filed
        return None

    @property
    def is_closed(self) -> bool:
        return self.state in (SlaState.RESOLVED, SlaState.REJECTED)
