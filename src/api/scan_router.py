"""Live "Scan this URL now" endpoint (DEMO-1) — multi-LLM ensemble.

This is the surface that proves the product works LIVE end-to-end, rather than
reading pre-seeded rows:

  1. Bright Data Web Unlocker **live-fetches** the suspect URL (real HTTP, real
     unlocked HTML) — the same verified-live lane as `tests/test_bd_live_smoke`.
  2. A **multi-LLM ensemble** scores the page LIVE: Claude (Anthropic) and
     GPT (OpenAI) each return an independent structured verdict, and a
     disagreement-aware merger picks the final verdict (majority vote; on
     dissent the confidence is discounted and it is flagged for human review).
     Gemini joins automatically when a working GEMINI_API_KEY is present.
  3. We return the merged verdict + each model's individual vote + which BD
     product was used + per-model latency + token counts + estimated cost, so a
     viewer can SEE it is a real multi-model decision, not canned.

Every call makes one real BD request and one real call per available LLM
(billable). On any live failure it returns ``mode='error'`` with the real
reason — it NEVER silently falls back to a mock, because the whole point is to
prove the live path.
"""
from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from ..common.logging import get_logger
from ..common.settings import get_settings

log = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["scan"])

# Rough public per-1K-token cost estimates (USD) for the demo cost line.
_COST = {
    "anthropic": (0.003, 0.015),   # (in, out) claude sonnet approx
    "openai": (0.0025, 0.01),      # gpt-4o approx
    "gemini": (0.00125, 0.005),    # gemini pro approx
}
_BD_UNLOCKER_USD = 0.0015          # per Web Unlocker request, approx
_HTML_CHARS_TO_MODEL = 6000        # cap HTML to bound latency + cost

_VERDICTS = ("benign", "suspicious", "phish")  # least -> most severe

_SYSTEM = (
    "You are an expert phishing analyst. You receive the raw HTML of a page "
    "fetched from the open web plus the brand it may be impersonating. Decide if "
    "the page is 'phish' (high-confidence brand impersonation), 'suspicious' "
    "(mixed signals) or 'benign' (not an impersonation). Be conservative: prefer "
    "'suspicious' when in doubt. Cite concrete evidence from the HTML you see; do "
    "not speculate beyond it."
)

# JSON schema shared by all providers (Anthropic tool / OpenAI function).
_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["phish", "suspicious", "benign"]},
        "confidence": {"type": "number"},
        "severity": {"type": "string",
                     "enum": ["critical", "high", "medium", "low"]},
        "evidence_summary": {"type": "array", "items": {"type": "string"}},
        "suggested_action": {"type": "string",
                             "enum": ["takedown", "watch", "dismiss"]},
    },
    "required": ["verdict", "confidence", "severity",
                 "evidence_summary", "suggested_action"],
}


class ScanRequest(BaseModel):
    url: str = Field(min_length=4, max_length=2048)
    brand: str = Field(default="the targeted brand", max_length=120)


def _prompt(url: str, brand: str, html: str) -> str:
    return (f"Suspected target brand: {brand}\n"
            f"Page URL: {url}\n\n"
            f"Raw HTML (truncated):\n{html[:_HTML_CHARS_TO_MODEL]}")


def _cost(provider: str, tin: int, tout: int) -> float:
    cin, cout = _COST.get(provider, (0.003, 0.015))
    return round((tin / 1000.0) * cin + (tout / 1000.0) * cout, 5)


# --------------------------------------------------------------------------- #
# Bright Data live fetch
# --------------------------------------------------------------------------- #

def _live_fetch(url: str) -> dict[str, Any]:
    import os
    os.environ["SPOOFVANE_BD_MODE"] = "live"
    if not os.getenv("BRIGHTDATA_API_TOKEN") and os.getenv("BRIGHTDATA_API_KEY"):
        os.environ["BRIGHTDATA_API_TOKEN"] = os.environ["BRIGHTDATA_API_KEY"]
    from ..integrations.brightdata.config import get_bd_config
    get_bd_config.cache_clear()
    from ..integrations.brightdata.clients import WebUnlockerClient
    t0 = time.time()
    res = WebUnlockerClient().unlock("scan", url)
    ms = int((time.time() - t0) * 1000)
    get_bd_config.cache_clear()
    return {"html": res.get("html", ""), "status": res.get("status"),
            "html_len": res.get("html_len", 0), "latency_ms": ms,
            "product": "Bright Data Web Unlocker"}


# --------------------------------------------------------------------------- #
# Per-provider live LLM verdicts. Each returns a normalized member dict or
# raises. A raise is caught by the ensemble and recorded as a skipped member,
# so one provider failing never fakes a result.
# --------------------------------------------------------------------------- #

def _claude_verdict(url: str, brand: str, html: str) -> dict[str, Any]:
    s = get_settings()
    if not s.anthropic_api_key:
        raise RuntimeError("no ANTHROPIC_API_KEY")
    from anthropic import Anthropic
    client = Anthropic(api_key=s.anthropic_api_key)
    tool = {"name": "submit_verdict", "description": "Submit a verdict.",
            "input_schema": _SCHEMA}
    t0 = time.time()
    resp = client.messages.create(
        model=s.anthropic_model, max_tokens=900, system=_SYSTEM, tools=[tool],
        tool_choice={"type": "tool", "name": "submit_verdict"},
        messages=[{"role": "user", "content": _prompt(url, brand, html)}],
    )
    ms = int((time.time() - t0) * 1000)
    data = next(b for b in resp.content if b.type == "tool_use").input
    return _member("Claude", s.anthropic_model, data, ms,
                   resp.usage.input_tokens, resp.usage.output_tokens, "anthropic")


def _gpt_verdict(url: str, brand: str, html: str) -> dict[str, Any]:
    s = get_settings()
    if not s.openai_api_key:
        raise RuntimeError("no OPENAI_API_KEY")
    from openai import OpenAI
    client = OpenAI(api_key=s.openai_api_key)
    fn = {"type": "function", "function": {
        "name": "submit_verdict", "description": "Submit a verdict.",
        "parameters": _SCHEMA}}
    t0 = time.time()
    resp = client.chat.completions.create(
        model=s.openai_model, max_tokens=900,
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": _prompt(url, brand, html)}],
        tools=[fn], tool_choice={"type": "function",
                                 "function": {"name": "submit_verdict"}},
    )
    ms = int((time.time() - t0) * 1000)
    call = resp.choices[0].message.tool_calls[0]
    data = json.loads(call.function.arguments)
    u = resp.usage
    return _member("GPT", s.openai_model, data, ms,
                   u.prompt_tokens, u.completion_tokens, "openai")


def _gemini_verdict(url: str, brand: str, html: str) -> dict[str, Any]:
    s = get_settings()
    key = getattr(s, "gemini_api_key", "")
    if not key:
        raise RuntimeError("no GEMINI_API_KEY")
    import urllib.request
    model = getattr(s, "gemini_model", "gemini-1.5-pro-latest")
    body = {
        "system_instruction": {"parts": [{"text": _SYSTEM}]},
        "contents": [{"parts": [{"text": _prompt(url, brand, html)
                                 + "\n\nRespond as compact JSON with keys: "
                                 "verdict, confidence, severity, "
                                 "evidence_summary (array), suggested_action."}]}],
        "generationConfig": {"response_mime_type": "application/json"},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=40) as r:
        doc = json.loads(r.read())
    ms = int((time.time() - t0) * 1000)
    txt = doc["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(txt)
    usage = doc.get("usageMetadata", {})
    return _member("Gemini", model, data, ms,
                   usage.get("promptTokenCount", 0),
                   usage.get("candidatesTokenCount", 0), "gemini")


def _member(name: str, model: str, data: dict, ms: int,
            tin: int, tout: int, provider: str) -> dict[str, Any]:
    # Normalize confidence to 0..1 (some models return 0..100).
    conf = float(data.get("confidence", 0.5))
    if conf > 1.0:
        conf = conf / 100.0
    conf = max(0.0, min(1.0, conf))
    return {
        "name": name, "model": model,
        "verdict": data["verdict"],
        "confidence": round(conf, 3),
        "severity": data.get("severity", "medium"),
        "evidence": list(data.get("evidence_summary", []))[:8],
        "suggested_action": data.get("suggested_action", "watch"),
        "latency_ms": ms, "tokens_in": tin, "tokens_out": tout,
        "cost_usd": _cost(provider, tin, tout),
    }


def _merge(members: list[dict[str, Any]]) -> dict[str, Any]:
    """Disagreement-aware merge: majority vote (tie -> most severe); discount
    confidence on dissent and flag for human review."""
    votes = [m["verdict"] for m in members]
    tally = {v: votes.count(v) for v in set(votes)}
    top = max(tally.values())
    winners = [v for v, n in tally.items() if n == top]
    verdict = max(winners, key=lambda v: _VERDICTS.index(v))
    dissent = len(set(votes)) > 1
    agreement = round(votes.count(verdict) / len(votes), 3)
    avg_conf = sum(m["confidence"] for m in members) / len(members)
    # graduated discount: full when unanimous, down to ~0.6 when split
    mult = 1.0 if not dissent else round(0.6 + 0.4 * agreement, 3)
    conf = round(avg_conf * mult, 3)
    # severity = the winning members' max severity
    sev_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    win_sev = [m["severity"] for m in members if m["verdict"] == verdict]
    severity = max(win_sev, key=lambda x: sev_rank.get(x, 1)) if win_sev else "medium"
    # union of evidence from winning members
    evidence: list[str] = []
    for m in members:
        if m["verdict"] == verdict:
            for e in m["evidence"]:
                if e not in evidence:
                    evidence.append(e)
    action = next((m["suggested_action"] for m in members
                   if m["verdict"] == verdict), "watch")
    return {
        "verdict": verdict, "confidence": conf, "severity": severity,
        "evidence": evidence[:8], "suggested_action": action,
        "dissent": dissent, "agreement_ratio": agreement,
        "escalate_to_human": dissent or verdict == "phish",
    }


def run_scan(url: str, brand: str = "the targeted brand") -> dict:
    """Core live scan: BD live-fetch -> multi-LLM ensemble -> merge.

    Pure of FastAPI so it can be driven by the ScanAgent (DEMO-3) as a governed,
    audited agent action AND by the HTTP endpoint. Never silently mocks.
    """
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    host = urlparse(url).hostname or url

    # 1) Live fetch via Bright Data.
    try:
        fetched = _live_fetch(url)
    except Exception as exc:  # noqa: BLE001
        log.error("scan_fetch_failed", url=url, error=str(exc))
        return {"mode": "error", "stage": "fetch", "url": url,
                "error": f"Bright Data live-fetch failed: {type(exc).__name__}: {exc}"}

    # 2) Multi-LLM ensemble — each provider scores the same HTML live.
    members: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for fn in (_claude_verdict, _gpt_verdict, _gemini_verdict):
        try:
            members.append(fn(url, brand, fetched["html"]))
        except Exception as exc:  # noqa: BLE001
            name = fn.__name__.replace("_verdict", "").lstrip("_")
            skipped.append({"model": name, "reason": f"{type(exc).__name__}: {exc}"[:160]})
            log.warning("scan_member_skipped", model=name, error=str(exc))

    if not members:
        return {"mode": "error", "stage": "verdict", "url": url,
                "error": "No LLM produced a live verdict.",
                "skipped": skipped,
                "fetch": {"product": fetched["product"],
                          "status": fetched["status"],
                          "html_len": fetched["html_len"],
                          "latency_ms": fetched["latency_ms"]}}

    merged = _merge(members)
    bd_cost = _BD_UNLOCKER_USD
    llm_cost = round(sum(m["cost_usd"] for m in members), 5)
    llm_latency = sum(m["latency_ms"] for m in members)
    return {
        "mode": "live",
        "url": url, "host": host, "brand": brand,
        "fetch": {
            "product": fetched["product"], "status": fetched["status"],
            "html_len": fetched["html_len"], "latency_ms": fetched["latency_ms"],
            "cost_usd": bd_cost,
        },
        # merged (ensemble) decision
        "verdict": merged["verdict"],
        "confidence": merged["confidence"],
        "severity": merged["severity"],
        "evidence": merged["evidence"],
        "suggested_action": merged["suggested_action"],
        "dissent": merged["dissent"],
        "agreement_ratio": merged["agreement_ratio"],
        "escalate_to_human": merged["escalate_to_human"],
        # per-model votes (the proof it is a real multi-LLM ensemble)
        "members": [
            {"name": m["name"], "model": m["model"], "verdict": m["verdict"],
             "confidence": m["confidence"], "latency_ms": m["latency_ms"],
             "tokens_in": m["tokens_in"], "tokens_out": m["tokens_out"],
             "cost_usd": m["cost_usd"]}
            for m in members
        ],
        "skipped": skipped,
        "models_used": [m["name"] for m in members],
        # back-compat single-model fields (first member)
        "model": members[0]["model"],
        "llm_latency_ms": llm_latency,
        "tokens_in": sum(m["tokens_in"] for m in members),
        "tokens_out": sum(m["tokens_out"] for m in members),
        "llm_cost_usd": llm_cost,
        "total_cost_usd": round(bd_cost + llm_cost, 5),
        "total_latency_ms": fetched["latency_ms"] + llm_latency,
    }


# --------------------------------------------------------------------------- #
# DEMO-3 — run the live scan as a governed, audited AGENT action.
# A process-local agent stack (kill-switch + hash-chained audit + governance)
# wraps run_scan so the live demo is genuinely agentic, not a bare API call.
# --------------------------------------------------------------------------- #
from ..agents.lifecycle import (  # noqa: E402
    AgentAuditLedger, GovernanceEngine, KillSwitch,
)

_SCAN_KILL = KillSwitch()
_SCAN_AUDIT = AgentAuditLedger()
_SCAN_GOV = GovernanceEngine(_SCAN_KILL, _SCAN_AUDIT)


def _scan_via_agent(url: str, brand: str, tenant_id: str = "demo-tenant") -> dict:
    """Run the scan through the ScanAgent so it is governed + hash-chain audited.

    Falls back to a direct run_scan if the agent layer is unavailable, so the
    endpoint never hard-fails on the agent wrapper.
    """
    try:
        from ..agents.agents import ScanAgent
        agent = ScanAgent(_SCAN_GOV)
        result = agent.run(tenant_id, {"url": url, "brand": brand})
        if result.halted:
            return {"mode": "error", "stage": "agent", "url": url,
                    "error": "Scan agent halted by kill-switch."}
        out = dict(result.output)
        last = _SCAN_AUDIT.entries()[-1] if _SCAN_AUDIT.entries() else None
        out["agent"] = {
            "name": agent.name,
            "state": result.state.value,
            "blast_radius": agent.blast_radius,
            "audit_seq": last.seq if last else None,
            "audit_verified": _SCAN_AUDIT.verify_chain(),
        }
        return out
    except Exception as exc:  # noqa: BLE001 - wrapper must never hard-fail the scan
        log.warning("scan_agent_fallback", error=str(exc))
        return run_scan(url, brand)


@router.post("/scan")
def scan(payload: ScanRequest = Body(...)) -> dict:
    """Live multi-LLM ensemble scan, run as a governed + audited agent action."""
    return _scan_via_agent(payload.url, payload.brand)
