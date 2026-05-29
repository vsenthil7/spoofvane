"""Sprint 7 — agent framework E1-E10 + kill-switch/governance/audit (§8 group E, §V8-5)."""
import pytest
from src.agents.lifecycle import (KillSwitch, AgentAuditLedger, GovernanceEngine,
                                   AgentState, SENSITIVE_AGENTS)
from src.agents.agents import (TakedownAgent, VictimIdAgent, CredPoisonAgent,
                               SynthPagesAgent, LearningAgent, SlmTriageAgent)


@pytest.fixture
def gov():
    ks = KillSwitch(); audit = AgentAuditLedger()
    return GovernanceEngine(ks, audit), ks, audit


def test_takedown_requires_hitl(gov):
    g, ks, audit = gov
    r = TakedownAgent(g).run("t", {"url": "https://e.top", "registrar": "nc"})
    assert r.state == AgentState.BLOCKED and r.blocked_on_hitl


def test_takedown_submits_after_hitl(gov):
    g, ks, audit = gov
    r = TakedownAgent(g).run("t", {"url": "https://e.top", "registrar": "nc"}, hitl_approved=True)
    assert r.state == AgentState.COMPLETE
    assert r.output["takedown_packet"]["submitted"] is True


def test_sensitive_agent_needs_lawful_basis(gov):
    g, ks, audit = gov
    r = VictimIdAgent(g).run("t", {"sessions": [1, 2]})
    assert r.blocked_on_hitl and "lawful basis" in r.output["reason"]


def test_egress_agent_jurisdiction_guard(gov):
    g, ks, audit = gov
    r = CredPoisonAgent(g).run("t", {"url": "https://e.top"}, region="RU",
                               lawful_basis="GDPR 6(1)(f)", hitl_approved=True, second_authoriser=True)
    assert not r.output.get("tracking_id")
    assert "forbidden in region" in r.output["reason"]


def test_egress_agent_two_person_rule(gov):
    g, ks, audit = gov
    # permitted region + basis + hitl but NO second authoriser -> blocked
    r = CredPoisonAgent(g).run("t", {"url": "https://e.top"}, region="US",
                               lawful_basis="GDPR 6(1)(f)", hitl_approved=True, second_authoriser=False)
    assert r.blocked_on_hitl


def test_egress_agent_full_authorisation(gov):
    g, ks, audit = gov
    r = CredPoisonAgent(g).run("t", {"url": "https://e.top"}, region="US",
                               lawful_basis="GDPR 6(1)(f)", hitl_approved=True, second_authoriser=True)
    assert r.state == AgentState.COMPLETE
    assert r.output["unique_per_url"] is True


def test_canary_unique_per_url(gov):
    g, ks, audit = gov
    a = CredPoisonAgent(g)
    kw = dict(region="US", lawful_basis="x", hitl_approved=True, second_authoriser=True)
    r1 = a.run("t", {"url": "https://a.top"}, **kw)
    r2 = a.run("t", {"url": "https://b.top"}, **kw)
    assert r1.output["tracking_id"] != r2.output["tracking_id"]


def test_kill_switch_halts_all(gov):
    g, ks, audit = gov
    ks.halt("t")
    r = TakedownAgent(g).run("t", {"url": "x"}, hitl_approved=True)
    assert r.state == AgentState.HALTED and r.halted


def test_kill_switch_scoped_per_tenant(gov):
    g, ks, audit = gov
    ks.halt("tenantA")
    assert ks.is_halted("tenantA") and not ks.is_halted("tenantB")


def test_kill_switch_global_and_resume(gov):
    g, ks, audit = gov
    ks.halt()  # global
    assert ks.is_halted("anyone")
    ks.resume()
    assert not ks.is_halted("anyone")


def test_agent_audit_chain_verifies(gov):
    g, ks, audit = gov
    SlmTriageAgent(g).run("t", {"evidence": {"composite": 0.3}})
    TakedownAgent(g).run("t", {"url": "x", "registrar": "nc"}, hitl_approved=True)
    assert audit.verify_chain() is True
    assert len(audit.entries()) >= 2


def test_audit_tamper_detected(gov):
    g, ks, audit = gov
    SlmTriageAgent(g).run("t", {"evidence": {"composite": 0.3}})
    audit.entries()[0].detail["tampered"] = True
    assert audit.verify_chain() is False


def test_learning_agent_produces_calibration_samples(gov):
    g, ks, audit = gov
    r = LearningAgent(g).run("t", {"analyst_overrides": [
        {"raw_score": 0.8, "corrected": "phish"},
        {"raw_score": 0.2, "corrected": "benign"}]})
    assert r.output["retrain_queued"]
    assert (0.8, 1) in r.output["calibration_samples"]


def test_synth_pages_isolated(gov):
    g, ks, audit = gov
    r = SynthPagesAgent(g).run("t", {"url": "https://e.top"}, region="US",
                               lawful_basis="x", hitl_approved=True, second_authoriser=True)
    assert r.output["isolated"] is True


def test_all_sensitive_agents_registered():
    assert {"victim_id_agent", "cred_poison_agent", "synth_pages_agent"} <= SENSITIVE_AGENTS
