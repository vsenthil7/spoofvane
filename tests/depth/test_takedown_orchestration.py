"""v07 W6 Gate — takedown orchestration differential probe.

A domain IoC routes to registrar+host+safebrowsing channels; a social IoC routes
to the platform channel; an app IoC to the store; SLA clock advances correctly on
state transitions; escalation tiers differ by channel cooperativeness. Live
submissions 🔒 BLOCKED-ENV (replay/mock).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from src.delivery.takedown.takedown_router import route_takedown, IocType, Channel
from src.delivery.takedown.escalation_ladder import EscalationLadder, EscalationTier
from src.delivery.takedown.takedown_sla import SlaTracker, SlaState


def test_domain_routes_to_multiple_channels():
    case = route_takedown("acme-login.top", IocType.DOMAIN)
    assert Channel.REGISTRAR in case.channels
    assert Channel.HOST in case.channels
    assert Channel.SAFEBROWSING in case.channels


def test_social_and_app_route_distinctly():
    social = route_takedown("@fake_acme", IocType.SOCIAL)
    app = route_takedown("com.fake.acme", IocType.APP)
    assert social.channels == [Channel.SOCIAL_PLATFORM]
    assert app.channels == [Channel.APP_STORE]
    # Materially different routing for different IoC types.
    assert social.channels != app.channels


def test_cert_routes_to_revocation():
    assert route_takedown("sha:x", IocType.CERT).channels == [Channel.CERT_REVOCATION]
    # URL routes to host+safebrowsing+apwg (no registrar, since it's a full URL).
    url_case = route_takedown("https://x.top/phish", IocType.URL)
    assert Channel.HOST in url_case.channels and Channel.REGISTRAR not in url_case.channels


def test_escalation_auto_vs_legal():
    ladder = EscalationLadder()
    domain_case = route_takedown("acme-login.top", IocType.DOMAIN)
    coop = ladder.decide(domain_case, host_cooperative=True)
    legal = ladder.decide(domain_case, host_cooperative=False)
    assert coop.tier == EscalationTier.AUTO
    assert legal.tier == EscalationTier.LEGAL
    assert coop.requires_human is False and legal.requires_human is True


def test_sla_clock_advances_on_transitions():
    t0 = datetime(2026, 5, 30, 0, 0, 0, tzinfo=timezone.utc)
    sla = SlaTracker()
    sla.history[0].ts = t0
    sla.transition(SlaState.ACKNOWLEDGED, t0 + timedelta(hours=2))
    sla.transition(SlaState.IN_PROGRESS, t0 + timedelta(hours=5))
    sla.transition(SlaState.RESOLVED, t0 + timedelta(hours=20))
    ttr = sla.time_to_resolution()
    assert ttr == timedelta(hours=20)
    assert sla.is_closed is True


def test_sla_illegal_transition_rejected():
    sla = SlaTracker()
    with pytest.raises(ValueError):
        sla.transition(SlaState.RESOLVED)  # can't jump FILED->RESOLVED


def test_sla_unresolved_returns_none():
    sla = SlaTracker()
    sla.transition(SlaState.ACKNOWLEDGED)
    assert sla.time_to_resolution() is None
    assert sla.is_closed is False
