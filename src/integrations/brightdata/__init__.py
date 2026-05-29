"""Canonical Bright Data integration package for SpoofVane.

This package is the single source of truth for all seven Bright Data products
used by SpoofVane. Per the convergence spec (Track A is the canonical source of
"verified-real BD discipline"), every discovery, inspection, and takedown module
imports its Bright Data access from here — there is no copy-pasted BD config
anywhere else in the tree.

The seven products (review §6 table):
  1. Scraping Browser (CDP)        -> ScrapingBrowserClient
  2. Residential Proxies           -> ResidentialProxyClient
  3. SERP API (brd_json=1)         -> SerpClient
  4. Web Unlocker                  -> WebUnlockerClient
  5. Web Scraper API               -> WebScraperClient
  6. Datasets / Marketplace        -> DatasetsClient
  7. Bright Data MCP Server        -> BrightDataMcpClient

Execution modes (review §V9-5 reproducible-build / replay requirement):
  * live    — real calls to brd.superproxy.io / api.brightdata.com using creds.
  * replay  — recorded golden fixtures replayed through the SAME client code
              paths, so the code under test is identical to live. Fixtures are
              input-dependent (review §V8-4: deterministic != constant).
  * mock    — deterministic synthetic responses for unit tests with no fixtures.

The mode is chosen by SPOOFVANE_BD_MODE (default: replay) so a reviewer on a
clean host with no BD account can still exercise every client code path.
"""
from __future__ import annotations

from .config import BrightDataConfig, BDMode, get_bd_config
from .base import BrightDataClient, BrightDataError, BrightDataUsage
from .cost import CostTracker, get_cost_tracker

__all__ = [
    "BrightDataConfig",
    "BDMode",
    "get_bd_config",
    "BrightDataClient",
    "BrightDataError",
    "BrightDataUsage",
    "CostTracker",
    "get_cost_tracker",
]

# Canonical product registry — the seven products, by id, for the sponsor ledger.
BD_PRODUCTS = {
    "scraping_browser": "Scraping Browser (CDP)",
    "residential_proxy": "Residential Proxies",
    "serp_api": "SERP API",
    "web_unlocker": "Web Unlocker",
    "web_scraper": "Web Scraper API",
    "datasets": "Datasets / Marketplace",
    "mcp_server": "Bright Data MCP Server",
}
