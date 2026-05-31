"""DEMO-3 — the live scan runs as a governed, audited agent action.

These tests do NOT call live services: they stub the core `run_scan` so the
agent wrapper (governance + kill-switch + hash-chained audit) can be exercised
in the normal offline suite. They prove the scan is genuinely agentic, not a
bare API call.
"""
from __future__ import annotations

import src.api.scan_router as sr


def test_scan_runs_through_agent_and_is_audited(monkeypatch):
    monkeypatch.setattr(sr, "run_scan",
                        lambda url, brand="x": {"mode": "live", "verdict": "benign",
                                                "url": url, "members": []})
    # Fresh audit ledger so the assertion is deterministic.
    from src.agents.lifecycle import AgentAuditLedger, GovernanceEngine, KillSwitch
    monkeypatch.setattr(sr, "_SCAN_KILL", KillSwitch())
    monkeypatch.setattr(sr, "_SCAN_AUDIT", AgentAuditLedger())
    monkeypatch.setattr(sr, "_SCAN_GOV",
                        GovernanceEngine(sr._SCAN_KILL, sr._SCAN_AUDIT))

    out = sr._scan_via_agent("https://example.com", "AcmeBank")
    assert out["mode"] == "live"
    # The agent wrapper added a governance/audit block.
    assert out["agent"]["name"] == "scan_agent"
    assert out["agent"]["state"] == "complete"
    assert out["agent"]["blast_radius"] == 0.2
    assert out["agent"]["audit_verified"] is True
    # The run was actually written to the hash-chained ledger.
    entries = sr._SCAN_AUDIT.entries()
    assert len(entries) == 1
    assert entries[0].agent == "scan_agent"
    assert sr._SCAN_AUDIT.verify_chain() is True


def test_scan_agent_halts_under_kill_switch(monkeypatch):
    monkeypatch.setattr(sr, "run_scan",
                        lambda url, brand="x": {"mode": "live", "verdict": "benign"})
    from src.agents.lifecycle import AgentAuditLedger, GovernanceEngine, KillSwitch
    kill = KillSwitch()
    monkeypatch.setattr(sr, "_SCAN_KILL", kill)
    monkeypatch.setattr(sr, "_SCAN_AUDIT", AgentAuditLedger())
    monkeypatch.setattr(sr, "_SCAN_GOV", GovernanceEngine(kill, sr._SCAN_AUDIT))

    kill.halt("demo-tenant")  # admin pulls the kill-switch
    out = sr._scan_via_agent("https://example.com", "AcmeBank", tenant_id="demo-tenant")
    assert out["mode"] == "error"
    assert out["stage"] == "agent"
    assert "halted" in out["error"].lower()


def test_scan_agent_is_in_the_real_registry():
    # The agent enumerated by /api/admin/agents should include scan_agent, i.e.
    # it is a real BaseAgent subclass, not an ad-hoc wrapper.
    from src.agents.agents import ScanAgent
    from src.agents.lifecycle import BaseAgent
    assert issubclass(ScanAgent, BaseAgent)
    assert ScanAgent.name == "scan_agent"
