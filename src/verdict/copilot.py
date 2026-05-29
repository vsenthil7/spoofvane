"""
AI Triage Copilot (v0.4) — an agentic Claude tool-use loop over DoppelDomain's
own data layer.

This is the "max AI usage" layer. v0.1–v0.3 used a single Claude *call* to reach
a per-page verdict. The Copilot is different in kind: it is a multi-turn agent
that an analyst (or an automated SOC workflow) talks to in natural language, and
that **autonomously decides which queries to run** against the alert/evidence
store to answer the question, then synthesises a grounded answer with citations
back to alert ids.

Example interactions it can handle end-to-end:
    "What are the critical open alerts for Acme Bank right now?"
    "Summarise today's social-media impersonation hits and which funnel to a
     credential page."
    "Draft the takedown for the highest-confidence phish and explain the
     evidence in plain English for our legal team."

Design choices that keep it consistent with the rest of the codebase:

* **Tool surface is the MCP contract.** The Copilot's tools are the exact
  read handlers already exposed by ``src.delivery.mcp_server`` (``query_alerts``,
  ``get_evidence``, ``draft_takedown``). Reusing them means the agent can do
  nothing a human MCP user couldn't, and there is one place to audit.
* **Read-only by default.** ``mark_triaged`` (the only state-mutating MCP tool)
  is *not* exposed to the agent unless ``allow_actions=True`` is passed
  explicitly. The product's hard rule — no AI auto-actions on consequential
  state — from the v0.3 human-in-the-loop review queue is preserved: even with
  actions enabled, the Copilot can only *move triage state*, never approve a
  takedown (that gate lives in ``src.common.review``).
* **Offline-safe.** When ``MOCK_MODE`` is set or no Anthropic key is configured,
  a deterministic planner answers a useful subset of intents by calling the same
  tools directly — so the demo and the test-suite run without network, exactly
  like ``VerdictEngine`` does.

The loop is bounded by ``max_iterations`` to guarantee termination.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ..common.logging import get_logger
from ..common.settings import get_settings
from ..delivery.mcp_server import (
    _draft_takedown,
    _get_evidence,
    _mark_triaged,
    _query_alerts,
)

log = get_logger(__name__)


_SYSTEM_PROMPT = """You are the DoppelDomain Triage Copilot, an expert \
phishing/brand-impersonation analyst embedded in a SOC.

You help analysts understand and act on brand-impersonation alerts. You have \
tools to query alerts, fetch the full evidence bundle for an alert, and return \
the pre-drafted takedown notice for an alert.

Rules:
- Ground every factual claim in tool results. Never invent an alert id, URL, \
score, or registrar. If you haven't fetched it, fetch it.
- Be concise and operational. Lead with the answer; analysts are busy.
- When you reference a specific alert, cite its id so the analyst can open it.
- You may *recommend* an action (takedown / watch / dismiss), but you never \
approve or send anything — a human owns that decision. Say so when relevant.
- If a question needs data you can get from a tool, call the tool rather than \
guessing or asking the analyst to look it up.

When you have enough information, give your final answer in plain prose."""


# Tool catalog presented to Claude. Schemas mirror the MCP server's, minus
# `mark_triaged` unless actions are explicitly enabled.
def _tool_specs(allow_actions: bool) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = [
        {
            "name": "query_alerts",
            "description": (
                "List alerts, optionally filtered by brand_id, status "
                "(open/triaged/confirmed/dismissed/closed), severity "
                "(critical/high/medium/low). Default limit 25, max 100."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "brand_id": {"type": "string"},
                    "status": {"type": "string"},
                    "severity": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                },
            },
        },
        {
            "name": "get_evidence",
            "description": (
                "Fetch the full evidence bundle for one alert: brand, "
                "inspection metadata, similarity scoring, and AI verdict."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"alert_id": {"type": "string"}},
                "required": ["alert_id"],
            },
        },
        {
            "name": "draft_takedown",
            "description": (
                "Return the pre-drafted (unsent) takedown notice for an alert."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"alert_id": {"type": "string"}},
                "required": ["alert_id"],
            },
        },
    ]
    if allow_actions:
        specs.append(
            {
                "name": "mark_triaged",
                "description": (
                    "Move an alert's triage status (triaged/dismissed/closed). "
                    "This does NOT approve or send a takedown."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "alert_id": {"type": "string"},
                        "status": {"type": "string"},
                        "notes": {"type": "string"},
                        "triaged_by": {"type": "string"},
                    },
                    "required": ["alert_id", "triaged_by"],
                },
            }
        )
    return specs


_READ_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "query_alerts": _query_alerts,
    "get_evidence": _get_evidence,
    "draft_takedown": _draft_takedown,
}
_ACTION_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "mark_triaged": _mark_triaged,
}


@dataclass
class CopilotStep:
    """One tool call made during the agent loop (for transparency/audit)."""

    tool: str
    arguments: dict[str, Any]
    ok: bool
    result_preview: str


@dataclass
class CopilotResult:
    answer: str
    steps: list[CopilotStep] = field(default_factory=list)
    model_used: str = ""
    iterations: int = 0


class TriageCopilot:
    """Agentic natural-language triage assistant."""

    def __init__(self, allow_actions: bool = False, max_iterations: int = 6) -> None:
        self.settings = get_settings()
        self.allow_actions = allow_actions
        self.max_iterations = max(1, max_iterations)
        self._handlers = dict(_READ_HANDLERS)
        if allow_actions:
            self._handlers.update(_ACTION_HANDLERS)

    # ─── Public API ────────────────────────────────────────────────────
    def ask(self, question: str, brand_id: str | None = None) -> CopilotResult:
        """Answer ``question`` autonomously, calling tools as needed."""
        if self._should_mock():
            return self._mock_answer(question, brand_id)
        try:
            return self._live_answer(question, brand_id)
        except Exception as exc:  # noqa: BLE001
            log.error("copilot.live_failed", error=str(exc))
            res = self._mock_answer(question, brand_id)
            res.answer = (
                "(AI service unavailable — answered from a direct query.)\n\n"
                + res.answer
            )
            return res

    # ─── Internals ─────────────────────────────────────────────────────
    def _should_mock(self) -> bool:
        return self.settings.mock_mode or not self.settings.anthropic_api_key

    def _dispatch(self, name: str, args: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        handler = self._handlers.get(name)
        if handler is None:
            return False, {"error": f"unknown or disabled tool: {name}"}
        try:
            return True, handler(args)
        except Exception as exc:  # noqa: BLE001
            return False, {"error": str(exc)}

    def _live_answer(self, question: str, brand_id: str | None) -> CopilotResult:
        from anthropic import Anthropic  # type: ignore

        client = Anthropic(api_key=self.settings.anthropic_api_key)
        tools = _tool_specs(self.allow_actions)

        seed = question if not brand_id else f"{question}\n\n(brand_id={brand_id})"
        messages: list[dict[str, Any]] = [{"role": "user", "content": seed}]
        steps: list[CopilotStep] = []

        for i in range(self.max_iterations):
            resp = client.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=1600,
                system=_SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            if resp.stop_reason != "tool_use":
                text = "".join(
                    b.text for b in resp.content if getattr(b, "type", None) == "text"
                )
                return CopilotResult(
                    answer=text.strip() or "(no answer produced)",
                    steps=steps,
                    model_used=self.settings.anthropic_model,
                    iterations=i + 1,
                )

            # Append the assistant turn, then satisfy each tool_use block.
            messages.append({"role": "assistant", "content": resp.content})
            tool_results: list[dict[str, Any]] = []
            for block in resp.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                ok, result = self._dispatch(block.name, dict(block.input))
                steps.append(
                    CopilotStep(
                        tool=block.name,
                        arguments=dict(block.input),
                        ok=ok,
                        result_preview=json.dumps(result, default=str)[:280],
                    )
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                        "is_error": not ok,
                    }
                )
            messages.append({"role": "user", "content": tool_results})

        # Hit the iteration ceiling — ask the model for a final answer with no
        # further tools.
        final = client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=1200,
            system=_SYSTEM_PROMPT
            + "\n\nYou have reached the tool-call limit. Answer now with what you have.",
            messages=messages,
        )
        text = "".join(
            b.text for b in final.content if getattr(b, "type", None) == "text"
        )
        return CopilotResult(
            answer=text.strip() or "(no answer produced within iteration budget)",
            steps=steps,
            model_used=self.settings.anthropic_model,
            iterations=self.max_iterations,
        )

    # ─── Offline planner ───────────────────────────────────────────────
    def _mock_answer(self, question: str, brand_id: str | None) -> CopilotResult:
        """Deterministic intent handling so the demo/tests work without a key.

        Covers the common analyst intents by calling the same tools the live
        agent would, then composing a grounded textual answer.
        """
        q = question.lower()
        steps: list[CopilotStep] = []

        # Decide the alert filter from the question.
        severity = None
        for sev in ("critical", "high", "medium", "low"):
            if sev in q:
                severity = sev
                break
        status = "open" if ("open" in q or "outstanding" in q or "new" in q) else None

        args: dict[str, Any] = {"limit": 25}
        if brand_id:
            args["brand_id"] = brand_id
        if severity:
            args["severity"] = severity
        if status:
            args["status"] = status

        ok, listing = self._dispatch("query_alerts", args)
        steps.append(
            CopilotStep("query_alerts", args, ok, json.dumps(listing, default=str)[:280])
        )
        alerts = listing.get("alerts", []) if ok else []

        wants_takedown = any(t in q for t in ("takedown", "draft", "notice"))
        wants_evidence = any(
            t in q for t in ("evidence", "why", "explain", "detail", "score")
        )

        lines: list[str] = []
        if not alerts:
            lines.append("No matching alerts found for that query.")
        else:
            filt = []
            if severity:
                filt.append(severity)
            if status:
                filt.append(status)
            label = (" ".join(filt) + " ") if filt else ""
            lines.append(f"Found {len(alerts)} {label}alert(s):")
            for a in alerts[:10]:
                lines.append(
                    f"  • [{a['id']}] {a['severity'].upper()} — {a['suspect_url']} "
                    f"(status: {a['status']})"
                )

            # Pick the most severe alert for deeper handling.
            order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            top = sorted(alerts, key=lambda a: order.get(a["severity"], 9))[0]

            if wants_evidence:
                eok, ev = self._dispatch("get_evidence", {"alert_id": top["id"]})
                steps.append(
                    CopilotStep(
                        "get_evidence",
                        {"alert_id": top["id"]},
                        eok,
                        json.dumps(ev, default=str)[:280],
                    )
                )
                if eok and ev.get("verdict"):
                    v = ev["verdict"]
                    sc = ev.get("scoring") or {}
                    lines.append("")
                    lines.append(f"Top alert [{top['id']}] evidence:")
                    lines.append(
                        f"  verdict={v['verdict']} confidence={v['confidence']:.2f} "
                        f"severity={v['severity']}"
                    )
                    if sc:
                        lines.append(
                            f"  scores: composite={sc.get('composite_score')} "
                            f"pHash={sc.get('phash_score')} DOM={sc.get('dom_score')}"
                        )
                    for e in v.get("evidence_summary", [])[:5]:
                        lines.append(f"    – {e}")

            if wants_takedown:
                tok, td = self._dispatch("draft_takedown", {"alert_id": top["id"]})
                steps.append(
                    CopilotStep(
                        "draft_takedown",
                        {"alert_id": top["id"]},
                        tok,
                        json.dumps(td, default=str)[:280],
                    )
                )
                if tok:
                    lines.append("")
                    lines.append(
                        f"Takedown draft for [{top['id']}] "
                        "(NOT sent — review and dispatch via your channel):"
                    )
                    lines.append(td.get("draft", "(no draft available)"))

        lines.append("")
        lines.append(
            "Note: I can recommend actions but a human owns approval — "
            "takedown submission stays gated behind your review queue."
        )

        return CopilotResult(
            answer="\n".join(lines),
            steps=steps,
            model_used="copilot-offline-planner-v1",
            iterations=1,
        )


def get_triage_copilot(allow_actions: bool = False) -> TriageCopilot:
    return TriageCopilot(allow_actions=allow_actions)
