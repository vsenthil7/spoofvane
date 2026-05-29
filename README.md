# DoppelDomain

> **Catch brand-impersonation infrastructure the day it goes live by fingerprinting the page itself — not just the domain name.**

**Track:** 3 — Security & Compliance
**Hackathon:** Bright Data — Web Data UNLOCKED (May 25–30, 2026)
**Status:** Prototype / hackathon build

---

## What it does

DoppelDomain monitors the open web for **pixel-perfect clones** of your brand's login, payment, and account pages — including the ones existing brand-protection tools miss: unrelated-looking domains hosting JS-heavy adversarial pages behind Cloudflare with geo-targeting.

It does this by combining:

1. **Discovery** — SERP API + certificate-transparency + new-domain feeds surface ~50K suspect URLs/day
2. **Inspection** — Bright Data Scraping Browser + Web Unlocker + geo-pinned residential proxies render the suspect pages in real Chrome from the target country, capturing screenshots, DOMs, network traffic, and JS bundle hashes
3. **Similarity scoring** — perceptual image hashing + DOM-tree similarity + CLIP-based logo detection
4. **AI verdict** — Claude Sonnet 4.6 (vision) reasons over screenshot + DOM + metadata and produces a structured `phish | suspicious | benign` verdict with evidence and a drafted takedown notice
5. **Delivery** — triage dashboard, evidence-pack PDF export, webhooks to Splunk/Sentinel/Slack, MCP server for analyst queries from Claude

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
doppeldomain/
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

## Licence

Hackathon prototype — all rights reserved during the judging window.

## Authors

Built for AT-Hack0023 — Bright Data Web Data UNLOCKED, May 2026.
