# DoppelDomain — Architecture

**Document:** 02 — Architecture
**Version:** 0.1 (hackathon prototype)
**Date:** 28 May 2026

---

## 1. System overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          CANONICAL BRAND ASSETS                            │
│  (login URL, payment URL, logo, brand colours, real-page DOM hash)         │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │ onboarding
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       DISCOVERY FEEDS  (parallel)                          │
│                                                                            │
│  • Bright Data SERP API — brand-targeted phishing queries                  │
│  • Certificate Transparency stream (certstream-compatible)                 │
│  • Newly-registered domain daily delta (public TLD zones)                  │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │ ~50K suspect URLs / day
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                      INSPECTION LAYER  (the unlock)                        │
│                                                                            │
│  • Bright Data Scraping Browser  — real headless Chrome                    │
│  • Bright Data Web Unlocker      — bypass anti-scanner walls               │
│  • Bright Data Proxies (residential, geo-targeted)                         │
│  → screenshot, DOM, network log, favicon, JS hashes                        │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          SIMILARITY SCORING                                │
│                                                                            │
│  • Perceptual hash (pHash)       — visual similarity                       │
│  • DOM tree similarity            — structural similarity                  │
│  • Logo detection (CLIP)          — brand-asset presence on non-brand TLD  │
│  • Favicon hash exact match                                                │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │ candidates above threshold
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                     AI VERDICT LAYER  (Claude Sonnet 4.6)                  │
│                                                                            │
│  • Multi-signal reasoning → phish | suspicious | benign                    │
│  • Confidence score                                                        │
│  • Drafts takedown request, per-registrar                                  │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                               DELIVERY                                     │
│                                                                            │
│  • Triage dashboard (FastAPI + Jinja)                                      │
│  • Evidence-pack PDF export (for registrar / hoster)                       │
│  • Webhook → Splunk / Sentinel / Slack                                     │
│  • Bright Data MCP Server → analyst queries from Claude                    │
└────────────────────────────────────────────────────────────────────────────┘
```

## 2. Components

### 2.1 `src/discovery`

Seven pluggable sources implementing the `DiscoverySource` protocol:

- `serp.py` — drives Bright Data SERP API with rotating phishing queries (organic)
- `cert_stream.py` — consumes a certstream-style firehose, filters by brand-adjacent tokens
- `new_domains.py` — daily TLD zone-file delta
- `paid_ads.py` *(v0.2)* — sponsored ads on brand keywords (SERP ad-slot)
- `mobile_app_store.py` *(v0.2)* — Play Store / App Store / APK sideload listings
- `github_leak.py` *(v0.2)* — phishing-kit repos, credential dumps, custom kit forks on public GitHub
- `telegram_kit.py` *(v0.2)* — Telegram channel and paste-site kit marketplace posts

All emit `SuspectURL(url, brand_id, source, discovered_at, discovery_metadata)` into the queue.

### 2.2 `src/inspection`

`browser.py` wraps the Bright Data Scraping Browser via the Chrome DevTools Protocol over WebSocket. Each `inspect()` call:

1. Acquires a residential-IP session pinned to `brand.target_country`
2. Navigates to the suspect URL with a randomised but realistic user-agent
3. Captures a full-page screenshot (PNG), DOM (HTML), network log (HAR), favicon, and JS bundle hashes
4. Writes evidence to S3 (or local FS in MOCK_MODE) with a SHA-256 content hash
5. Returns an `InspectionResult`

The Web Unlocker is engaged automatically by Bright Data when a 403 / JS challenge is detected — no per-page configuration is needed.

`multi_region.py` *(v0.2)* orchestrates parallel inspections from N regions and computes pairwise pHash + DOM similarity, surfacing geo-cloaking divergence. `diff_detector.py` *(v0.2)* re-inspects previously-benign URLs and detects time-bomb activations (a URL that flips from a holding page to a phishing payload between inspections).

### 2.3 `src/scoring`

Six scorers run against the canonical:

| Scorer | Library | Signal |
| --- | --- | --- |
| `phash.py` | `imagehash` | Perceptual screenshot similarity (Hamming distance) |
| `dom_similarity.py` | custom | Tree-edit-distance + tag-frequency cosine |
| `logo.py` | colour histogram | Logo presence in top-left of suspect screenshot |
| `logo_embedding.py` *(v0.2)* | CLIP `clip-ViT-B-32` or spatial-histogram fallback | Robust logo similarity surviving re-colour / re-scale |
| `favicon.py` | MD5 | Exact-match flag for the favicon byte stream |
| `family.py` *(v0.2)* | rule-based regex | Attack-family classification (m365 / banking / crypto / payment / support / generic) |
| `template_fingerprint.py` *(v0.2)* | BeautifulSoup + signature regex | Match against known phishing-kit families (16Shop / EvilProxy / Caffeine / Tycoon-2FA / GreatHorn / Modlishka) including JS-bundle-hash matching |

A `composite_score` is computed as a weighted average. When a family classification with confidence ≥ 0.6 is in hand the composite uses *family-specific weight overrides* (e.g. crypto pages weight DOM signals heavier; M365 pages weight visual layout). Pages above `BRAND.threshold` OR with cloaking-detected proceed to verdict.

### 2.4 `src/verdict`

`claude_verdict.py` calls Claude Sonnet 4.6 with a multimodal payload:

- The full-page screenshot
- The canonical screenshot, for comparison
- A JSON block of metadata (URL, registrar, ASN, registration date, DOM excerpt, scoring sub-scores)

The model is constrained via a strict JSON schema (Anthropic tool-use mode) to return:

```jsonc
{
  "verdict": "phish",
  "confidence": 0.94,
  "severity": "critical",
  "evidence_summary": [
    "Renders Acme logo identically to canonical",
    "Login form posts to non-Acme domain (account-update-portal.xyz)",
    "Domain registered 2 days ago via Namecheap",
    "Hosted on a low-reputation ASN (AS204957)"
  ],
  "suggested_action": "takedown",
  "takedown_draft": "Dear Namecheap Abuse Team, ..."
}
```

### 2.5 `src/delivery`

- `pdf_evidence.py` — bundles screenshot + DOM + WHOIS + verdict + detection signals into a PDF via ReportLab
- `webhooks.py` — fans IOCs out to Slack, Splunk HEC, and the four enterprise integrations below
- `integration_base.py` *(v0.2)* — shared HMAC-signing + retry-with-backoff + severity mapping
- `servicenow.py` *(v0.2)* — creates ITSM incidents with severity-mapped impact/urgency
- `sentinel.py` *(v0.2)* — Microsoft Sentinel Log Analytics Data Collector with SharedKey HMAC-SHA256 auth
- `pagerduty.py` *(v0.2)* — Events API v2 trigger/resolve with `dedup_key=alert_id`
- `taxii.py` *(v0.2)* — STIX 2.1 indicator+malware+relationship bundles to TAXII 2.1 collections
- `takedown/` — registrar abuse-report submission (Cloudflare, Namecheap, GoDaddy)
- `mcp_server.py` — exposes Bright Data MCP Server tools to Claude for analyst conversations

### 2.6 `src/storage`

SQLAlchemy models against SQLite (dev) or Postgres (prod). Core tables:

| Table | Purpose |
| --- | --- |
| `brands` | One row per onboarded brand; v0.2 adds `tenant_id` for isolation |
| `suspect_urls` | One row per discovered URL with discovery metadata |
| `inspections` | One row per inspection attempt, FK → `suspect_urls`, with evidence pointers and hash-chain row hash |
| `scorings` | One row per composite-score computation |
| `verdicts` | One row per AI verdict; v0.2 adds `attack_family`, `kit_match`, `cloaking_detected`, `cloaking_evidence` |
| `alerts` | The triage queue; v0.2 adds `tenant_id` |
| `tenants` *(v0.2)* | One row per tenant with plan + daily caps |
| `api_keys` *(v0.2)* | API keys with hashed secrets, scopes, expiry, revocation |
| `cost_events` *(v0.2)* | One row per Bright Data API call billed to a tenant |
| `feedback_events` *(v0.2)* | Analyst triage outcomes — active-learning signal |
| `audit_log` *(v0.2)* | Append-only state-change record with actor + IP + before/after |

Evidence blobs (screenshots, DOMs, HARs) live in S3 (or `data/evidence/` in MOCK_MODE), keyed by SHA-256.

### 2.7 `src/api`

FastAPI app with route auth via `Depends(require_auth(scope))`. Routes:

- `GET /healthz` — liveness
- `POST /api/brands` (`brands:write`) / `GET /api/brands` (`brands:read`)
- `POST /api/discovery/run` (`discovery:run`)
- `GET /api/alerts` (`alerts:read`) / `POST /api/alerts/{id}/triage` (`alerts:triage`)
- `GET /api/alerts/{id}/evidence.pdf` (`alerts:read`)
- `POST /api/admin/tenants` *(v0.2)* (`admin:*`) — tenant lifecycle
- `POST /api/admin/tenants/{id}/keys` *(v0.2)* (`admin:*`) — issue API key
- `GET /api/admin/tenants/{id}/costs` *(v0.2)* (`admin:*`) — spend view
- `GET /api/admin/audit-log` *(v0.2)* (`admin:*`) — audit query
- HTML pages: `/` (dashboard), `/alerts/{id}`, `/audit` *(v0.2)*

## 3. Data flow (per suspect URL)

```
SuspectURL ─► InspectionResult ─► ScoringResult ─► Verdict ─► Alert
                 │                       │              │         │
                 │                       │              │         ├─► webhook fan-out
                 │                       │              │         │   (Slack/Splunk/ServiceNow/Sentinel/PagerDuty/TAXII)
                 │                       │              │         ├─► PDF export
                 │                       │              │         ├─► MCP exposure
                 │                       │              │         └─► takedown automation (manual approval)
                 │                       │              │
                 │                       │              ├─► attack_family classification (v0.2)
                 │                       │              ├─► kit fingerprint match (v0.2)
                 │                       │              └─► geo-cloaking signal (v0.2)
                 │                       │
                 │                       └─► family-specific weight profile (v0.2)
                 │
                 └─► evidence blobs (S3, SHA-256 keyed, hash-chained)
```

## 4. Deployment

### Dev (this repo, MOCK_MODE)

- SQLite at `data/doppeldomain.db`
- Local filesystem for evidence at `data/evidence/`
- All Bright Data calls return fixture data
- All Claude calls return canned verdicts unless `ANTHROPIC_API_KEY` is set
- `uvicorn src.api.app:app --reload` boots everything

### Hackathon demo (single VM, real Bright Data, real Claude)

- Same SQLite + local FS
- `BRIGHTDATA_*` and `ANTHROPIC_API_KEY` set; `MOCK_MODE=false`
- Discovery + inspection + verdict run in the same FastAPI process via background tasks (no Celery for the demo)

### Production target

- Postgres 16 + S3
- Celery workers behind Redis for inspection burst capacity (target: 5K URLs/hour)
- Inspection workers are stateless and horizontally scalable
- Verdict layer rate-limited at the model provider, with a backing queue
- Triage dashboard fronted by a reverse proxy + SSO (Okta / Entra)

## 5. Security and tamper-evidence

- Every evidence blob is content-addressed (SHA-256) and the hash is recorded in the database
- The `inspections` table records the immutable hash chain `prev_hash || row_hash` — any after-the-fact tampering is detectable
- Takedown PDFs include the SHA-256 of each embedded artefact in a manifest page
- Per-brand API keys are stored in a vault, not in Postgres
- No PII from inspected pages is persisted beyond the evidence blob — DOM dumps are searched for credential-style strings and those substrings are redacted before insert
