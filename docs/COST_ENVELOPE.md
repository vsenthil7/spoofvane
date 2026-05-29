# Cost Envelope (review §V9-3)

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST

Per-tenant monthly envelope enforced by `CostTracker.over_envelope`. Indicative
unit costs (USD) in `cost.py`; real values come from the BD invoice.

| Tier | Monthly envelope (USD) |
|------|------------------------|
| free | 5 |
| pro | 100 |
| business | 1,000 |
| enterprise | 25,000 |

Unit costs (µ$/action): scraping_browser 0.015 · residential_proxy 0.001 ·
serp_api 0.0025 · web_unlocker 0.004 · web_scraper 0.003 · datasets 0.0008 ·
mcp_server 0.002. SLM-first routing (D4) keeps ≥70% of low-severity verdicts on
the cheap path. Enforcement tested in `test_envelope_enforcement`.
