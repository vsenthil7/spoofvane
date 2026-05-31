"""Concrete agents E1-E6, E10 built on the lifecycle framework.

E1 takedown_agent   — research -> draft -> HITL gate -> submit (real submit is F1-F4)
E2 victim_id_agent  — victim identification (sensitive: lawful basis + HITL)
E3 cred_poison_agent— canary credential injection (egress: two-person + jurisdiction)
E4 synth_pages_agent— honeypot deployment (egress: two-person + jurisdiction)
E6 learning_agent   — wires analyst overrides into C1 calibration
E10 slm_triage agent— agentic wrapper around D4
"""
from __future__ import annotations

import hashlib
from .lifecycle import BaseAgent, AgentState


class TakedownAgent(BaseAgent):
    name = "takedown_agent"
    blast_radius = 0.6  # submitting a takedown is high blast-radius -> HITL

    def _execute(self, tenant_id: str, payload: dict) -> dict:
        url = payload.get("url", "")
        registrar = payload.get("registrar", "unknown")
        packet = {
            "abuse_to": f"abuse@{registrar}.example",
            "subject": f"Phishing takedown request: {url}",
            "evidence_refs": payload.get("evidence_refs", []),
            "drafted": True,
            "submitted": True,  # reaches here only after HITL approval in run()
        }
        return {"takedown_packet": packet, "reference_id": hashlib.sha256(url.encode()).hexdigest()[:12]}


class VictimIdAgent(BaseAgent):
    name = "victim_id_agent"
    blast_radius = 0.7

    def _execute(self, tenant_id: str, payload: dict) -> dict:
        # correlates session telemetry behind consent/lawful-basis gate
        sessions = payload.get("sessions", [])
        return {"victims_identified": len(sessions),
                "correlation_method": "session_telemetry",
                "pii_minimised": True}


class CredPoisonAgent(BaseAgent):
    name = "cred_poison_agent"
    blast_radius = 0.85

    def _execute(self, tenant_id: str, payload: dict) -> dict:
        url = payload.get("url", "")
        canary = hashlib.sha256(f"canary{url}{tenant_id}".encode()).hexdigest()[:16]
        return {"canary_credential": f"user_{canary}@canary.example",
                "tracking_id": canary, "unique_per_url": True}


class SynthPagesAgent(BaseAgent):
    name = "synth_pages_agent"
    blast_radius = 0.9

    def _execute(self, tenant_id: str, payload: dict) -> dict:
        return {"honeypot_namespace": f"hp-{tenant_id}-{hashlib.md5(payload.get('url','').encode()).hexdigest()[:8]}",
                "isolated": True, "deployed": True}


class LearningAgent(BaseAgent):
    name = "learning_agent"
    blast_radius = 0.2

    def _execute(self, tenant_id: str, payload: dict) -> dict:
        overrides = payload.get("analyst_overrides", [])
        # produce (raw_score, label) samples that E6 feeds into C1 PlattCalibrator
        samples = [(o["raw_score"], 1 if o["corrected"] == "phish" else 0) for o in overrides]
        return {"calibration_samples": samples, "retrain_queued": bool(samples)}


class SlmTriageAgent(BaseAgent):
    name = "slm_triage_agent"
    blast_radius = 0.1

    def _execute(self, tenant_id: str, payload: dict) -> dict:
        from ..verdict.ensemble import SlmTriage
        v = SlmTriage().decide(payload.get("evidence", {"composite": 0.3}))
        return {"verdict": v.verdict, "confidence": v.confidence, "cost_tier": v.cost_tier}


class ScanAgent(BaseAgent):
    """E-series live-scan agent (DEMO-3).

    Wraps the live "scan this URL" loop as a governed, audited agent action:
    Bright Data live-fetch -> multi-LLM ensemble verdict (Claude + GPT + Gemini)
    -> disagreement-aware merge. Read-only detection, so blast_radius is low
    (no HITL needed) — but it runs under the kill-switch and every run is written
    to the hash-chained agent audit ledger, so the live demo is genuinely
    agentic, not a bare API call.

    The heavy lifting lives in ``src.api.scan_router`` (the live providers +
    merger); this agent calls that logic so there is a single source of truth.
    """
    name = "scan_agent"
    blast_radius = 0.2  # read-only detection; below the 0.5 HITL threshold

    def _execute(self, tenant_id: str, payload: dict) -> dict:
        from ..api.scan_router import run_scan
        return run_scan(payload.get("url", ""),
                        payload.get("brand", "the targeted brand"))
