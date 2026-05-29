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

Three pluggable sources implementing the `DiscoverySource` protocol:

- `serp.py` — drives Bright Data SERP API with rotating phishing queries
- `cert_stream.py` — consumes a certstream-style firehose, filters by brand-adjacent tokens
- `new_domains.py` — daily TLD zone-file delta

All emit `SuspectURL(url, brand_id, source, discovered_at)` into the queue.

### 2.2 `src/inspection`

`browser.py` wraps the Bright Data Scraping Browser via the Chrome DevTools Protocol over WebSocket. Each `inspect()` call:

1. Acquires a residential-IP session pinned to `brand.target_country`
2. Navigates to the suspect URL with a randomised but realistic user-agent
3. Captures a full-page screenshot (PNG), DOM (HTML), network log (HAR), favicon, and JS bundle hashes
4. Writes evidence to S3 (or local FS in MOCK_MODE) with a SHA-256 content hash
5. Returns an `InspectionResult`

The Web Unlocker is engaged automatically by Bright Data when a 403 / JS challenge is detected — no per-page configuration is needed.

### 2.3 `src/scoring`

Four scorers run in parallel against the canonical:

| Scorer | Library | Signal |
| --- | --- | --- |
| `phash.py` | `imagehash` | Perceptual screenshot similarity (Hamming distance) |
| `dom_similarity.py` | custom | Tree-edit-distance + tag-frequency cosine |
| `logo.py` | OpenAI CLIP (open weights, `clip-ViT-B-32`) | Logo presence anywhere on the suspect page |
| `favicon.py` | MD5 | Exact-match flag for the favicon byte stream |

A `composite_score` is computed as a weighted average, with weights tuned per brand. Pages above `BRAND.threshold` proceed to verdict.

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

- `dashboard.py` — Jinja2 triage UI mounted by FastAPI
- `pdf_evidence.py` — bundles screenshot + DOM + WHOIS + verdict into a PDF via WeasyPrint
- `webhooks.py` — fans IOCs out to Slack, Splunk HEC, Microsoft Sentinel
- `mcp_server.py` — exposes the Bright Data MCP Server tools to Claude so analysts can `query_alerts(filter=...)` from inside a Claude conversation

### 2.6 `src/storage`

SQLAlchemy models against SQLite (dev) or Postgres (prod). Three core tables:

| Table | Purpose |
| --- | --- |
| `brands` | One row per onboarded brand with canonical asset hashes |
| `suspect_urls` | One row per discovered URL with discovery metadata |
| `inspections` | One row per inspection attempt, FK → `suspect_urls`, with all evidence pointers |
| `verdicts` | One row per AI verdict, FK → `inspections` |
| `alerts` | The triage queue — one row per "phish" or "suspicious" verdict |

Evidence blobs (screenshots, DOMs, HARs) live in S3 (or `data/evidence/` in MOCK_MODE), keyed by SHA-256.

## 3. Data flow (per suspect URL)

```
SuspectURL ─► InspectionResult ─► ScoringResult ─► Verdict ─► Alert
                       │                                       │
                       └─► evidence blobs (S3)                 └─► webhook fan-out
                                                                   PDF export
                                                                   MCP exposure
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
