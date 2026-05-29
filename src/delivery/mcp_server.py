"""
MCP server — analyst-facing tools usable from Claude (and any other MCP host).

Exposes four tools:

* ``query_alerts``  — list alerts, optionally filtered by brand / status / severity
* ``get_evidence``  — fetch the full bundle (brand + inspection + scoring + verdict)
                      for a given alert id
* ``draft_takedown`` — return the takedown draft text for a given alert id
* ``mark_triaged``  — mark an alert as triaged

Wire format is JSON-RPC 2.0 over stdio, which is the transport MCP hosts use
when running a server as a subprocess. We implement the three lifecycle
methods (``initialize``, ``tools/list``, ``tools/call``) directly — using the
``mcp`` SDK would pull in a non-trivial dependency tree for what is, at this
scale, a few JSON dispatch lines.

Run via::

    python -m src.delivery.mcp_server

A Claude Desktop / IDE MCP host can then add an entry like::

    {
      "doppeldomain": {
        "command": "python",
        "args": ["-m", "src.delivery.mcp_server"]
      }
    }

to surface these tools to the analyst.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any, Callable

from ..common.logging import get_logger
from ..common.models import AlertStatus, Severity
from ..storage.db import session_scope
from ..storage.repositories import (
    AlertRepo,
    BrandRepo,
    InspectionRepo,
    ScoringRepo,
    VerdictRepo,
)

logger = get_logger(__name__)

SERVER_NAME = "doppeldomain"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"


# --------------------------------------------------------------------------- #
# Tool implementations
# --------------------------------------------------------------------------- #


def _query_alerts(args: dict[str, Any]) -> dict[str, Any]:
    brand_id = args.get("brand_id")
    status_raw = args.get("status")
    severity_raw = args.get("severity")
    limit = int(args.get("limit", 25))
    limit = max(1, min(limit, 100))

    status = AlertStatus(status_raw) if status_raw else None
    severity = Severity(severity_raw) if severity_raw else None

    with session_scope() as s:
        alerts = AlertRepo(s).list_for_brand(
            brand_id=brand_id, status=status, severity=severity, limit=limit
        )
    return {
        "count": len(alerts),
        "alerts": [_alert_summary(a) for a in alerts],
    }


def _get_evidence(args: dict[str, Any]) -> dict[str, Any]:
    alert_id = _required(args, "alert_id")
    with session_scope() as s:
        alert = AlertRepo(s).get(alert_id)
        if alert is None:
            raise _ToolError(f"alert not found: {alert_id}")
        brand = BrandRepo(s).get(alert.brand_id)
        inspection = InspectionRepo(s).get(alert.inspection_id)
        scoring = ScoringRepo(s).get(alert.inspection_id)
        verdict = VerdictRepo(s).get(alert.verdict_id)

    return {
        "alert": _alert_summary(alert),
        "brand": {"id": brand.id, "name": brand.name} if brand else None,
        "inspection": (
            {
                "id": inspection.id,
                "final_url": inspection.final_url,
                "asn": inspection.asn,
                "registrar": inspection.registrar,
                "registration_date": _iso(inspection.registration_date),
                "rendered_country": inspection.rendered_country,
                "screenshot_hash": inspection.screenshot_hash,
                "dom_hash": inspection.dom_hash,
            }
            if inspection
            else None
        ),
        "scoring": (
            {
                "phash_score": scoring.phash_score,
                "dom_score": scoring.dom_score,
                "logo_score": scoring.logo_score,
                "favicon_match": scoring.favicon_match,
                "composite_score": scoring.composite_score,
                "above_threshold": scoring.above_threshold,
            }
            if scoring
            else None
        ),
        "verdict": (
            {
                "verdict": verdict.verdict.value,
                "confidence": verdict.confidence,
                "severity": verdict.severity.value,
                "evidence_summary": verdict.evidence_summary,
                "suggested_action": verdict.suggested_action,
                "model_used": verdict.model_used,
            }
            if verdict
            else None
        ),
    }


def _draft_takedown(args: dict[str, Any]) -> dict[str, Any]:
    alert_id = _required(args, "alert_id")
    with session_scope() as s:
        alert = AlertRepo(s).get(alert_id)
        if alert is None:
            raise _ToolError(f"alert not found: {alert_id}")
        verdict = VerdictRepo(s).get(alert.verdict_id)
    if verdict is None:
        raise _ToolError(f"verdict missing for alert {alert_id}")
    return {
        "alert_id": alert_id,
        "draft": verdict.takedown_draft,
        "note": "Draft only — review and dispatch via your established channel.",
    }


def _mark_triaged(args: dict[str, Any]) -> dict[str, Any]:
    alert_id = _required(args, "alert_id")
    status_raw = args.get("status", "triaged")
    notes = args.get("notes")
    triaged_by = _required(args, "triaged_by")
    status = AlertStatus(status_raw)

    with session_scope() as s:
        repo = AlertRepo(s)
        if repo.get(alert_id) is None:
            raise _ToolError(f"alert not found: {alert_id}")
        updated = repo.update_triage(
            alert_id, status=status, notes=notes, actor=triaged_by
        )
    return {"alert": _alert_summary(updated)}


# --------------------------------------------------------------------------- #
# Tool catalog
# --------------------------------------------------------------------------- #

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "query_alerts",
        "description": (
            "List DoppelDomain alerts, optionally filtered by brand_id, "
            "status (open/triaged/closed/false_positive), severity "
            "(critical/high/medium/low), with a default limit of 25 and max 100."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "brand_id": {"type": "string"},
                "status": {"type": "string", "enum": [s.value for s in AlertStatus]},
                "severity": {"type": "string", "enum": [s.value for s in Severity]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_evidence",
        "description": (
            "Fetch the full evidence bundle for a single alert: brand, "
            "inspection metadata, similarity scoring, and AI verdict."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"alert_id": {"type": "string"}},
            "required": ["alert_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "draft_takedown",
        "description": (
            "Return the pre-drafted takedown notice for an alert. The draft "
            "has NOT been sent — it is intended for analyst review."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"alert_id": {"type": "string"}},
            "required": ["alert_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "mark_triaged",
        "description": (
            "Update an alert's triage status to triaged / closed / false_positive."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "alert_id": {"type": "string"},
                "status": {"type": "string", "enum": [s.value for s in AlertStatus]},
                "notes": {"type": "string"},
                "triaged_by": {"type": "string"},
            },
            "required": ["alert_id", "triaged_by"],
            "additionalProperties": False,
        },
    },
]

_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "query_alerts": _query_alerts,
    "get_evidence": _get_evidence,
    "draft_takedown": _draft_takedown,
    "mark_triaged": _mark_triaged,
}


# --------------------------------------------------------------------------- #
# JSON-RPC plumbing
# --------------------------------------------------------------------------- #


class _ToolError(RuntimeError):
    """Raised by tool handlers when the input is invalid or no row exists."""


def handle_request(req: dict[str, Any]) -> dict[str, Any] | None:
    """Dispatch a single JSON-RPC request. Returns None for notifications."""
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}

    # Notifications have no id and expect no response.
    is_notification = "id" not in req

    try:
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            }
        elif method == "tools/list":
            result = {"tools": _TOOLS}
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if name not in _HANDLERS:
                return _error(req_id, -32601, f"unknown tool: {name}")
            try:
                tool_result = _HANDLERS[name](arguments)
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(tool_result, default=str, indent=2),
                        }
                    ],
                    "isError": False,
                }
            except _ToolError as exc:
                result = {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                }
        elif method in ("notifications/initialized", "notifications/cancelled"):
            return None
        else:
            return _error(req_id, -32601, f"method not found: {method}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("mcp.unhandled", method=method)
        return _error(req_id, -32603, f"internal error: {exc}")

    if is_notification:
        return None
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _alert_summary(a) -> dict[str, Any]:
    return {
        "id": a.id,
        "brand_id": a.brand_id,
        "suspect_url": a.suspect_url,
        "severity": a.severity.value,
        "status": a.status.value,
        "created_at": _iso(a.created_at),
        "triaged_by": a.triaged_by,
        "triaged_at": _iso(a.triaged_at),
    }


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _required(args: dict[str, Any], key: str) -> Any:
    if key not in args or args[key] in (None, ""):
        raise _ToolError(f"missing required argument: {key}")
    return args[key]


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    """Read JSON-RPC frames from stdin (one per line), write replies to stdout."""
    logger.info("mcp.start", server=SERVER_NAME, version=SERVER_VERSION)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stdout.write(json.dumps(_error(None, -32700, f"parse error: {exc}")) + "\n")
            sys.stdout.flush()
            continue
        resp = handle_request(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, default=str) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
