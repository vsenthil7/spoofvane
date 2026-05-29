"""F8 — SpoofVane's adapter to Bright Data's MCP Server (analyst-in-Claude-Desktop).

Lets an analyst trigger an ad-hoc BD-routed render from inside the copilot, via
Bright Data's hosted MCP server. Wraps the canonical BrightDataMcpClient so the
call is cost-tracked and audited like every other BD product.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..integrations.brightdata.clients import BrightDataMcpClient


@dataclass
class BdMcpRenderResult:
    tool: str
    result_id: str
    rendered_via: str
    ok: bool


class BdMcpClient:
    def __init__(self, tenant_id: str = "demo") -> None:
        self.tenant_id = tenant_id
        self._client = BrightDataMcpClient()

    def render_markdown(self, url: str) -> BdMcpRenderResult:
        res = self._client.tool_call(self.tenant_id, "scrape_as_markdown", {"url": url})
        return BdMcpRenderResult(
            tool="scrape_as_markdown", result_id=res["result_id"],
            rendered_via=res["rendered_via"], ok=res["ok"],
        )

    def search_engine(self, query: str, engine: str = "google") -> BdMcpRenderResult:
        res = self._client.tool_call(self.tenant_id, "search_engine",
                                     {"query": query, "engine": engine})
        return BdMcpRenderResult(
            tool="search_engine", result_id=res["result_id"],
            rendered_via=res["rendered_via"], ok=res["ok"],
        )
