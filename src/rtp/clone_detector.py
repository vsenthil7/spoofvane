"""W8 clone detector: a foreign-origin asset load opens an alert; same-origin
does not."""
from __future__ import annotations

from dataclasses import dataclass

from .beacon_ingest import BeaconEvent


@dataclass
class CloneVerdict:
    is_clone: bool
    opens_alert: bool
    reason: str
    risk: float


def detect_clone(event: BeaconEvent) -> CloneVerdict:
    """If the real site's beacon fires from a foreign origin, the page is a
    clone serving the real assets => open an alert. Same-origin is benign."""
    if event.is_foreign_origin:
        return CloneVerdict(
            is_clone=True, opens_alert=True,
            reason=f"beacon for {event.site} fired from foreign origin {event.origin}",
            risk=0.9,
        )
    return CloneVerdict(
        is_clone=False, opens_alert=False,
        reason="same-origin load (legitimate)", risk=0.0,
    )
