# Bright Data Sponsor Usage Ledger (review §6, §2.2)

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST

The five mandatory evidence points per product: runtime code · demo seed · cost
row · audit ledger · UI badge. Cost rows are emitted automatically by
`src/integrations/brightdata/cost.py` on every call.

| # | Product | Client | Runtime code | Cost row | Modules |
|---|---------|--------|--------------|----------|---------|
| 1 | Scraping Browser (CDP) | `ScrapingBrowserClient` | 🟢 | 🟢 `scraping_browser` | B1, B8, F1 |
| 2 | Residential Proxies | `ResidentialProxyClient` | 🟢 | 🟢 `residential_proxy` | A3, A6, B1 |
| 3 | SERP API | `SerpClient` | 🟢 | 🟢 `serp_api` | A1 |
| 4 | Web Unlocker | `WebUnlockerClient` | 🟢 | 🟢 `web_unlocker` | A6, A9 |
| 5 | Web Scraper API | `WebScraperClient` | 🟢 | 🟢 `web_scraper` | A2, A8, B8 |
| 6 | Datasets / Marketplace | `DatasetsClient` | 🟢 | 🟢 `datasets` | A4, B7 |
| 7 | Bright Data MCP Server | `BrightDataMcpClient` / `BdMcpClient` | 🟢 | 🟢 `mcp_server` | F8 |

**🔒 BLOCKED-ENV:** live 24h-green smoke against brd.superproxy.io needs a BD
account + outbound network; replay mode exercises all client code paths credential-free.
