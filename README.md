# SpoofVane

> **Catch brand-impersonation infrastructure the day it goes live by fingerprinting the page itself — not just the domain name.**

**Track:** 3 — Security & Compliance
**Hackathon:** Bright Data — Web Data UNLOCKED (May 25–30, 2026)
**Status:** v0.4 — prototype with detection depth, discovery breadth (now incl. social channel), an agentic AI triage copilot, and enterprise platform foundations

Changelogs, newest first: [v0.4](docs/12-v04-changelog.md) (social channel + AI triage copilot) · [v0.3](docs/11-v03-changelog.md) (IAM, RBAC, MFA, SSO, audit, HITL, reports) · [v0.2](docs/09-v02-changelog.md) (detection + discovery depth). All framed honestly against the [enterprise readiness gaps](docs/08-enterprise-readiness.md).

---

## What it does

SpoofVane monitors the open web for **pixel-perfect clones** of your brand's login, payment, and account pages — including the ones existing brand-protection tools miss: unrelated-looking domains hosting JS-heavy adversarial pages behind Cloudflare with geo-targeting.

It does this by combining:

1. **Discovery** — 8 sources (SERP organic + paid ads, certificate transparency, new-domain delta, Play Store / App Store / APK sideload, GitHub kit leaks, Telegram kit marketplace, and social-platform impersonation across X / Instagram / Facebook / TikTok / LinkedIn / YouTube / Telegram / Threads) surface 100+ suspect URLs per brand-sweep
2. **Inspection** — Bright Data Scraping Browser + Web Unlocker + geo-pinned residential proxies render suspect pages in real Chrome from the target country. Optional **multi-region inspection** renders from N countries in parallel and detects geo-cloaking divergence
3. **Similarity scoring** — perceptual image hashing + DOM-tree similarity + CLIP-or-spatial-histogram logo detection + favicon MD5
4. **Attack-family + kit fingerprinting** — classifies into m365 / banking / crypto / payment / support kit families, matches against known phishing-kit signatures (16Shop, EvilProxy, Caffeine, Tycoon-2FA, GreatHorn, Modlishka)
5. **AI verdict** — Claude Sonnet 4.6 (vision) reasons over screenshot + DOM + metadata and produces a structured `phish | suspicious | benign` verdict with evidence and a drafted takedown notice
6. **AI triage copilot** — an agentic Claude tool-use loop an analyst talks to in natural language ("show me the critical open alerts and draft a takedown for the worst one"); it autonomously queries the alert/evidence store via the same MCP tool contract, cites alert ids, and is read-only by default (it can never approve or send a takedown — that gate stays with a human)
7. **Delivery** — triage dashboard with family/kit/cloaking signal cards, evidence-pack PDF export, webhooks to ServiceNow + Sentinel + PagerDuty + STIX/TAXII + Slack + Splunk + generic HMAC-signed webhooks, MCP server for analyst queries from Claude, registrar takedown automation (Cloudflare / Namecheap / GoDaddy)
8. **Platform** — multi-tenancy with API keys + scopes, audit log, per-tenant cost attribution, active-learning feedback loop

## Why it needs Bright Data

| Bright Data product | Role |
| --- | --- |
| **Scraping Browser** | Render adversarial pages with real headless Chrome |
| **Web Unlocker** | Punch through anti-scanner walls phishing kits put up *specifically to block security scanners* |
| **SERP API** | Track Google results for brand-targeted phishing keywords |
| **Residential proxies (geo-targeted)** | Catch phishing pages that only render in the victim country |
| **MCP Server** | Let analysts query the system from Claude during incident response |

**5 of 7 Bright Data products with the most justified technical dependency of any Track 3 entry.** No other stack can reliably reach the adversarial pages this product is built to find.

## Quick start

```bash
# 1. Install
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp config/.env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY and BRIGHTDATA_* keys
# (the prototype runs in MOCK_MODE=true without real keys)

# 3. Initialise local DB
python -m src.storage.init_db

# 4. Onboard a brand (canonical login page)
python -m scripts.onboard_brand \
  --name "Example Bank" \
  --login-url "https://example-bank.com/login" \
  --logo data/canonical/example-bank-logo.png

# 5. Run a discovery + inspection pass
python -m src.discovery.run_once --brand "Example Bank"

# 6. Start the triage dashboard
uvicorn src.api.app:app --reload
# Open http://localhost:8000
```

Set `MOCK_MODE=true` in `.env` to run end-to-end with fixture data (no network calls, no API keys needed). This is the default for the hackathon demo.

## Repository layout

```
spoofvane/
├── README.md                      ← you are here
├── requirements.txt
├── docs/
│   ├── 01-product-spec.md         ← full product spec
│   ├── 02-architecture.md         ← system design
│   ├── 03-api-reference.md        ← REST + MCP surface
│   ├── 04-runbook.md              ← operations / incident response
│   ├── 05-demo-script.md          ← 3-minute hackathon demo
│   └── 06-judging-fit.md          ← how this scores on each rubric axis
├── config/
│   └── .env.example
├── src/
│   ├── common/                    ← models, settings, logging
│   ├── discovery/                 ← SERP + CT-log + newly-reg-domain feeds
│   ├── inspection/                ← Bright Data Scraping Browser wrapper
│   ├── scoring/                   ← pHash, DOM-similarity, CLIP-logo
│   ├── verdict/                   ← Claude Sonnet 4.6 verdict + takedown
│   ├── delivery/                  ← webhooks (Splunk/Sentinel/Slack), PDF
│   ├── storage/                   ← Postgres / SQLite + S3 (local fs)
│   ├── api/                       ← FastAPI app + triage dashboard
│   └── web/                       ← Jinja templates + static assets
├── scripts/
│   ├── onboard_brand.py           ← register canonical assets
│   └── seed_demo.py               ← load fixture data for demo
├── tests/                         ← pytest
└── data/
    ├── canonical/                 ← real-brand canonical screenshots/DOMs
    ├── evidence/                  ← captured suspect pages
    └── reports/                   ← exported takedown PDFs
```

## Documentation

| Document | What it covers |
| --- | --- |
| [docs/01-product-spec.md](docs/01-product-spec.md) | Problem, users, use cases, scope |
| [docs/02-architecture.md](docs/02-architecture.md) | Components, data flow, storage, deployment |
| [docs/03-api-reference.md](docs/03-api-reference.md) | REST endpoints + MCP tool surface |
| [docs/04-runbook.md](docs/04-runbook.md) | Day-2 ops, alerts, incident playbooks |
| [docs/05-demo-script.md](docs/05-demo-script.md) | 3-minute live demo for judging |
| [docs/06-judging-fit.md](docs/06-judging-fit.md) | Per-rubric-axis self-assessment |
| [docs/07-competitive-analysis.md](docs/07-competitive-analysis.md) | 13-vendor feature matrix, head-to-heads, realistic ARR bands |
| [docs/08-enterprise-readiness.md](docs/08-enterprise-readiness.md) | Procurement-checklist gap analysis with effort estimates |

## Licence

Hackathon prototype — all rights reserved during the judging window.

## Authors

Built for AT-Hack0023 — Bright Data Web Data UNLOCKED, May 2026.
