# SpoofVane — Runbook

**Document:** 04 — Runbook
**Version:** 0.1 (hackathon prototype)
**Date:** 28 May 2026

---

## 1. Day-1 setup

### 1.1 Prerequisites

- Python 3.11+
- Bright Data account with Scraping Browser, Web Unlocker, SERP API, and residential proxies enabled
- Anthropic API key with access to Claude Sonnet 4.6
- (Optional) Postgres 16 if not using the bundled SQLite

### 1.2 Install

```bash
git clone <repo>
cd spoofvane
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/.env.example .env
```

Edit `.env`:

```bash
MOCK_MODE=false
ANTHROPIC_API_KEY=sk-ant-...
BRIGHTDATA_CDP_ENDPOINT=wss://brd.superproxy.io:9222
BRIGHTDATA_API_KEY=...
BRIGHTDATA_PROXY_USER=...
BRIGHTDATA_PROXY_PASS=...
BRIGHTDATA_SERP_HOST=brd.superproxy.io:33335
DATABASE_URL=sqlite:///data/spoofvane.db
EVIDENCE_DIR=data/evidence
```

### 1.3 Initialise

```bash
python -m src.storage.init_db
python -m scripts.onboard_brand --name "Example Bank" --login-url "https://example-bank.com/login" --logo data/canonical/example-bank-logo.png --target-country GB
```

### 1.4 Start the service

```bash
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

Visit <http://localhost:8000>.

## 2. Day-2 operations

### 2.1 Daily checks

| Check | Where | What to look for |
| --- | --- | --- |
| Discovery throughput | `/admin/discovery/throughput` | URLs/hour per source — flat lines mean a feed broke |
| Inspection success rate | `/admin/inspection/success` | > 90% expected; sudden drops mean Bright Data session pool churn |
| Verdict confidence histogram | `/admin/verdicts/confidence` | Bimodal is healthy (phish-cluster + benign-cluster); flat means model degradation |
| Open alert age (P95) | `/admin/alerts/age` | < 4 hours target |

### 2.2 Common alerts

#### `DISCOVERY_FEED_STALLED`
A discovery source produced 0 URLs in 30 minutes.

**Action:** check the relevant adapter logs (`src/discovery/<source>.py`); most often a credential expiry or upstream outage.

#### `INSPECTION_REPEATED_403`
A specific URL pattern is returning 403 on > 5 attempts.

**Action:** raise the Web Unlocker tier for that brand or add a fingerprint randomisation rule.

#### `VERDICT_DRIFT`
The phish/benign confidence histogram has flattened (Gini < 0.4).

**Action:** sanity-check 10 recent verdicts manually. If the model is mis-calibrating, fall back to the rule-only mode while a new prompt is rolled.

#### `EVIDENCE_HASH_MISMATCH`
A stored evidence blob's hash doesn't match the recorded value.

**Action:** treat as a security incident. Page the on-call. Do not proceed with takedowns sourced from that evidence until the chain is verified.

### 2.3 Incident playbooks

#### Playbook A — Phishing campaign in flight

1. Confirm at least one `CRITICAL` alert is open
2. Pull the cluster via `query_alerts(severity=critical, since=now-1h)`
3. Generate a campaign evidence pack: `python -m scripts.bundle_campaign <alert_ids...>`
4. Fire the bundled pack to the registrar abuse channel
5. Push IOCs (domains, IPs, ASNs, JS hashes) to Splunk via the bundled webhook config

#### Playbook B — False-positive surge

1. Alert age P50 is climbing because analysts are dismissing too many
2. Run `python -m scripts.calibrate --brand <brand_id> --days 7` to refit per-brand thresholds against analyst dismissal patterns
3. Roll the new threshold gradually (canary 10% → 100% over 24h)

#### Playbook C — Bright Data quota exhaustion

1. Inspection latency P95 jumps from ~8s to > 60s
2. Check Bright Data dashboard for residential traffic exhaustion
3. Throttle discovery to high-value sources only (`cert_stream` off, `serp` only) until quota resets

## 3. Backup and restore

- The Postgres database is backed up nightly via `pg_dump`
- The evidence S3 bucket has versioning on; objects are immutable for 90 days
- The hash chain in `inspections` is exported daily to cold storage as a tamper-evidence anchor
