"""W6 escalation ladder: auto -> analyst -> legal.

Auto-files where a cooperative channel exists; escalates to analyst, then legal,
otherwise (the realistic ZeroFox-vs-Bolster model — not a fake universal
"60-second" claim).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .takedown_router import Channel, TakedownCase


class EscalationTier(str, Enum):
    AUTO = "auto"        # cooperative channel, auto-filed
    ANALYST = "analyst"  # needs analyst review/manual filing
    LEGAL = "legal"      # needs legal escalation (uncooperative host/jurisdiction)


# Channels that support automated, cooperative filing.
_COOPERATIVE = {Channel.SAFEBROWSING, Channel.APWG, Channel.REGISTRAR,
                Channel.SOCIAL_PLATFORM, Channel.APP_STORE}
# Channels/cases that typically require legal pressure.
_LEGAL_PRONE = {Channel.HOST}


@dataclass
class EscalationDecision:
    tier: EscalationTier
    reason: str
    requires_human: bool


class EscalationLadder:
    def decide(self, case: TakedownCase, host_cooperative: bool = True) -> EscalationDecision:
        """Decide the escalation tier for a case."""
        chans = set(case.channels)
        if chans & _COOPERATIVE and host_cooperative:
            return EscalationDecision(
                EscalationTier.AUTO,
                "cooperative channel available; auto-file (human-confirm gated)",
                requires_human=False,
            )
        if not host_cooperative or (chans & _LEGAL_PRONE and not (chans & _COOPERATIVE)):
            return EscalationDecision(
                EscalationTier.LEGAL,
                "uncooperative host/jurisdiction; legal escalation required",
                requires_human=True,
            )
        return EscalationDecision(
            EscalationTier.ANALYST,
            "no fully-cooperative channel; analyst review required",
            requires_human=True,
        )
