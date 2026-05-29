"""Agent lifecycle + kill-switch + governance + agent audit (E5-E9 core).

Every agent runs inside this framework. The framework enforces:
  * E7 kill_switch — admin hard-halt; all running agents observe it and return
    {"halted": true} within the poll window.
  * E8 governance — every action is scored for blast-radius and checked against
    the tenant cost/risk envelope; above threshold -> HITL required.
  * E9 agent_audit — every agent action is appended to a hash-chained ledger.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    BLOCKED = "blocked"      # awaiting HITL
    HALTED = "halted"        # kill-switch
    COMPLETE = "complete"
    ERROR = "error"


# ---- E7 kill switch -----------------------------------------------------
class KillSwitch:
    """Process-local kill switch (Redis pubsub in production, ≤5s propagation)."""

    def __init__(self) -> None:
        self._halted_tenants: set[str] = set()
        self._global = False

    def halt(self, tenant_id: str | None = None) -> None:
        if tenant_id is None:
            self._global = True
        else:
            self._halted_tenants.add(tenant_id)

    def resume(self, tenant_id: str | None = None) -> None:
        if tenant_id is None:
            self._global = False
        else:
            self._halted_tenants.discard(tenant_id)

    def is_halted(self, tenant_id: str) -> bool:
        return self._global or tenant_id in self._halted_tenants


# ---- E9 agent audit (hash-chained) --------------------------------------
@dataclass
class AgentAuditEntry:
    seq: int
    tenant_id: str
    agent: str
    action: str
    detail: dict
    prev_hash: str
    this_hash: str
    ts: str
    lawful_basis: str | None = None


class AgentAuditLedger:
    def __init__(self) -> None:
        self._entries: list[AgentAuditEntry] = []

    def append(self, tenant_id: str, agent: str, action: str, detail: dict,
               lawful_basis: str | None = None) -> AgentAuditEntry:
        seq = len(self._entries)
        prev = self._entries[-1].this_hash if self._entries else "0" * 64
        ts = datetime.now(timezone.utc).isoformat()
        body = f"{seq}|{tenant_id}|{agent}|{action}|{sorted(detail.items())}|{prev}|{ts}|{lawful_basis}"
        this_hash = hashlib.sha256(body.encode()).hexdigest()
        e = AgentAuditEntry(seq, tenant_id, agent, action, detail, prev, this_hash, ts, lawful_basis)
        self._entries.append(e)
        return e

    def verify_chain(self) -> bool:
        prev = "0" * 64
        for e in self._entries:
            body = f"{e.seq}|{e.tenant_id}|{e.agent}|{e.action}|{sorted(e.detail.items())}|{prev}|{e.ts}|{e.lawful_basis}"
            if hashlib.sha256(body.encode()).hexdigest() != e.this_hash or e.prev_hash != prev:
                return False
            prev = e.this_hash
        return True

    def entries(self) -> list[AgentAuditEntry]:
        return list(self._entries)


# ---- E8 governance ------------------------------------------------------
@dataclass
class GovernanceDecision:
    allowed: bool
    requires_hitl: bool
    requires_second_authoriser: bool
    blast_radius: float
    reason: str
    lawful_basis: str | None = None


# Modules that are offensive / PII-sensitive (review §V8-5).
SENSITIVE_AGENTS = {"victim_id_agent", "cred_poison_agent", "synth_pages_agent", "exec_attack_surface"}
# Jurisdictions where E3/E4 are permitted to be enabled per-tenant.
EGRESS_PERMITTED_REGIONS = {"US", "GB"}


class GovernanceEngine:
    def __init__(self, kill_switch: KillSwitch, audit: AgentAuditLedger,
                 hitl_threshold: float = 0.5) -> None:
        self.kill = kill_switch
        self.audit = audit
        self.hitl_threshold = hitl_threshold

    def evaluate(self, tenant_id: str, agent: str, action: str,
                 blast_radius: float, region: str = "US",
                 lawful_basis: str | None = None) -> GovernanceDecision:
        if self.kill.is_halted(tenant_id):
            return GovernanceDecision(False, False, False, blast_radius,
                                      "kill-switch engaged for tenant")
        sensitive = agent in SENSITIVE_AGENTS
        egress = agent in {"cred_poison_agent", "synth_pages_agent"}
        # §V8-5: sensitive agents require a named lawful basis
        if sensitive and not lawful_basis:
            return GovernanceDecision(False, True, False, blast_radius,
                                      "sensitive agent requires named lawful basis", None)
        # §V8-5: hard jurisdiction guard for egress agents
        if egress and region not in EGRESS_PERMITTED_REGIONS:
            return GovernanceDecision(False, False, False, blast_radius,
                                      f"egress agent forbidden in region {region}", lawful_basis)
        requires_hitl = sensitive or blast_radius >= self.hitl_threshold
        requires_second = egress  # two-person rule for credential/honeypot egress
        return GovernanceDecision(
            allowed=True, requires_hitl=requires_hitl,
            requires_second_authoriser=requires_second,
            blast_radius=blast_radius,
            reason="permitted within envelope" if not requires_hitl else "HITL required",
            lawful_basis=lawful_basis,
        )


# ---- agent base ---------------------------------------------------------
@dataclass
class AgentResult:
    agent: str
    state: AgentState
    output: dict = field(default_factory=dict)
    halted: bool = False
    blocked_on_hitl: bool = False


class BaseAgent:
    name = "base"
    blast_radius = 0.1

    def __init__(self, governance: GovernanceEngine) -> None:
        self.gov = governance
        self.state = AgentState.IDLE

    def run(self, tenant_id: str, payload: dict, region: str = "US",
            lawful_basis: str | None = None,
            hitl_approved: bool = False, second_authoriser: bool = False) -> AgentResult:
        decision = self.gov.evaluate(tenant_id, self.name, "run",
                                     self.blast_radius, region, lawful_basis)
        if not decision.allowed:
            if self.gov.kill.is_halted(tenant_id):
                self.state = AgentState.HALTED
                return AgentResult(self.name, self.state, {"reason": decision.reason}, halted=True)
            self.state = AgentState.BLOCKED
            return AgentResult(self.name, self.state, {"reason": decision.reason}, blocked_on_hitl=True)
        if decision.requires_hitl and not hitl_approved:
            self.state = AgentState.BLOCKED
            self.gov.audit.append(tenant_id, self.name, "blocked_hitl", {"reason": decision.reason},
                                  decision.lawful_basis)
            return AgentResult(self.name, self.state, {"reason": "awaiting HITL approval"},
                               blocked_on_hitl=True)
        if decision.requires_second_authoriser and not second_authoriser:
            self.state = AgentState.BLOCKED
            self.gov.audit.append(tenant_id, self.name, "blocked_second_auth",
                                  {"reason": "two-person rule"}, decision.lawful_basis)
            return AgentResult(self.name, self.state, {"reason": "awaiting second authoriser"},
                               blocked_on_hitl=True)
        out = self._execute(tenant_id, payload)
        self.gov.audit.append(tenant_id, self.name, "executed", {"keys": sorted(out.keys())},
                              decision.lawful_basis)
        self.state = AgentState.COMPLETE
        return AgentResult(self.name, self.state, out)

    def _execute(self, tenant_id: str, payload: dict) -> dict:
        raise NotImplementedError
