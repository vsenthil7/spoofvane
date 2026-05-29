# DoppelDomain — API reference

**Document:** 03 — API reference
**Version:** 0.1 (hackathon prototype)
**Date:** 28 May 2026

---

DoppelDomain exposes two interfaces:

1. A **REST API** over FastAPI for the dashboard and for direct integration
2. An **MCP server** for analyst use inside Claude

---

## 1. REST API

Base path: `http://localhost:8000` in dev.
All endpoints return JSON unless explicitly noted. `application/json` content type assumed.

### 1.1 Brands

#### `POST /api/brands`
Onboard a new brand.

**Request**
```json
{
  "name": "Example Bank",
  "login_url": "https://example-bank.com/login",
  "payment_url": "https://example-bank.com/checkout",
  "logo_path": "data/canonical/example-bank-logo.png",
  "target_country": "GB",
  "brand_keywords": ["example bank", "examplebank", "ex-bank"]
}
```

**Response — 201**
```json
{
  "id": "brand_01HXYZ...",
  "name": "Example Bank",
  "canonical_screenshot_hash": "a3f8...",
  "canonical_dom_hash": "9c41...",
  "logo_clip_embedding_id": "emb_01HXYZ..."
}
```

#### `GET /api/brands`
List all onboarded brands.

#### `GET /api/brands/{brand_id}`
Single brand detail including current alert counts.

---

### 1.2 Discovery

#### `POST /api/discovery/run`
Trigger a one-off discovery pass for a brand.

**Request**
```json
{ "brand_id": "brand_01HXYZ...", "sources": ["serp", "cert_stream", "new_domains"] }
```

**Response — 202**
```json
{ "job_id": "job_01HXYZ...", "queued_urls": 412 }
```

#### `GET /api/discovery/jobs/{job_id}`
Status of a discovery run.

---

### 1.3 Inspection

#### `POST /api/inspect`
Inspect a single URL on demand (used for manual triage).

**Request**
```json
{ "brand_id": "brand_01HXYZ...", "url": "https://account-update-portal.xyz/login" }
```

**Response — 200**
```json
{
  "inspection_id": "insp_01HXYZ...",
  "screenshot_url": "/api/evidence/a3f8.../screenshot.png",
  "dom_hash": "9c41...",
  "scores": { "phash": 0.96, "dom": 0.81, "logo": 0.93, "favicon": true },
  "composite_score": 0.91
}
```

---

### 1.4 Verdicts and alerts

#### `GET /api/alerts`
List alerts. Query params: `status` (`open` | `triaged` | `closed`), `severity`, `brand_id`, `limit`, `offset`.

#### `GET /api/alerts/{alert_id}`
Full alert detail including verdict, evidence pointers, and takedown draft.

#### `POST /api/alerts/{alert_id}/triage`
Mark triage action.

**Request**
```json
{ "action": "takedown_filed", "notes": "Filed with Namecheap abuse" }
```

#### `GET /api/alerts/{alert_id}/evidence.pdf`
Stream the evidence-pack PDF (Content-Type: `application/pdf`).

---

### 1.5 Webhooks

#### `POST /api/webhooks`
Register a destination for IOC fan-out.

**Request**
```json
{
  "brand_id": "brand_01HXYZ...",
  "destination": "slack",
  "config": { "webhook_url": "https://hooks.slack.com/..." },
  "min_severity": "high"
}
```

Supported destinations: `slack`, `splunk_hec`, `sentinel`, `generic_webhook`.

---

## 2. MCP server

DoppelDomain exposes a Bright Data MCP-compatible server so analysts can query alerts directly from Claude during an incident.

Endpoint: `ws://localhost:8000/mcp` (development).

### Tools

#### `query_alerts`
List or filter alerts.

**Input schema**
```jsonc
{
  "brand_id": "string (optional)",
  "status":   "open | triaged | closed (optional)",
  "severity": "critical | high | medium | low (optional)",
  "since":    "ISO-8601 datetime (optional)",
  "limit":    "integer, default 20"
}
```

**Output:** array of alert summaries — `{id, brand, url, severity, verdict, confidence, discovered_at}`.

#### `get_evidence`
Return the full evidence pack for an alert.

**Input:** `{ "alert_id": "string" }`

**Output:** `{ screenshot_url, dom_excerpt, whois, network_log_summary, verdict, takedown_draft }`

#### `draft_takedown`
Re-draft a takedown notice for an alert, optionally with custom instructions.

**Input:** `{ "alert_id": "string", "registrar": "string (optional)", "tone": "formal | urgent | legal (optional)" }`

**Output:** `{ "takedown_text": "..." }`

#### `mark_triaged`
Mark an alert as triaged.

**Input:** `{ "alert_id": "string", "action": "string", "notes": "string" }`

**Output:** `{ "ok": true }`

### Example MCP session (analyst inside Claude)

> **Analyst:** *Use the DoppelDomain MCP. Show me all critical open alerts for Example Bank from the last 24 hours.*
>
> **Claude:** *Calls `query_alerts(brand_id="brand_01HXYZ", severity="critical", status="open", since="2026-05-27T00:00:00Z")` → returns 3 alerts → presents them in a table → offers to draft takedowns for all three.*

---

## 3. Error model

All error responses share a single shape:

```json
{
  "error": {
    "code": "BRAND_NOT_FOUND",
    "message": "No brand with id brand_01HXYZ exists",
    "request_id": "req_01HXYZ..."
  }
}
```

| Code | HTTP | Meaning |
| --- | --- | --- |
| `BRAND_NOT_FOUND` | 404 | Brand ID does not exist |
| `INVALID_URL` | 400 | URL failed validation |
| `INSPECTION_FAILED` | 502 | Bright Data could not reach the page after N retries |
| `VERDICT_FAILED` | 502 | The verdict model call failed |
| `RATE_LIMITED` | 429 | Per-brand rate limit hit |
| `INTERNAL` | 500 | Unexpected error — `request_id` is loggable |

## 4. Authentication

The prototype uses a single shared API key passed in the `X-API-Key` header. Production deploys integrate OAuth2 + SSO (out of scope for the hackathon prototype).
