# SpoofVane — Product Specification

**Document:** 01 — Product Spec
**Version:** 0.1 (hackathon prototype)
**Date:** 28 May 2026

---

## 1. Problem statement

Brand impersonation is one of the most damaging entry vectors for credential theft and customer fraud. A large brand-protection market already exists — Netcraft, ZeroFox, BrandShield, Bolster, MarkMonitor, Recorded Future, and others compete in this space, with mature platforms and seven-figure ARR contracts. **SpoofVane is not a replacement for any of them.**

The wedge SpoofVane addresses is a specific, narrow blind spot in that existing stack: **phishing infrastructure that incumbents physically cannot reach with their current scanning approach.**

### The specific blind spot

Modern phishing kits use four techniques together that defeat most external scanners:

1. **Unrelated-looking domains** (`account-update-portal[.]xyz`) — defeats keyword and typosquat filters
2. **Geo-targeted rendering** — the payload only serves to IPs in the victim country; a US-only phishing page returns clean content to any EU scanner
3. **Cloudflare / Akamai / hCaptcha fronting** — scanners receive a 403 or a JS challenge instead of the page
4. **JS-heavy adversarial DOM** — the cloned login page only assembles client-side, so naive HTTP-fetch scanners see an empty shell

Reaching these pages at scale requires three things together:

1. Real Chrome (not curl) — for JS-rendered DOM
2. Residential IPs pinned to the victim's country — for geo-targeting
3. Anti-bot challenge bypass — for the fronting layer

This is exactly the capability surface Bright Data's Scraping Browser + Web Unlocker + residential proxies were built for. SpoofVane is the application of that capability surface to the phishing-detection problem.

### What is NOT novel

To be clear about prior art:

- **Visual + DOM similarity for phishing detection** has been published academically since the 2008 PhishZoo / Medvet work, and is a known capability inside Netcraft, BrandShield, and Bolster.
- **Headless browser rendering for phishing analysis** is standard at Netcraft.
- **Certificate-transparency monitoring** is offered by virtually every vendor in the space.

### What IS the defensible wedge

The combination of:

- Geo-pinned residential rendering as a *first-class* per-brand setting (most competitors have datacentre-heavy crawl pools)
- Web Unlocker integration so anti-bot-fronted pages still produce a fingerprint-able render
- A hash-chained evidence ledger that survives registrar scrutiny
- A delivery model that emits the result *into the customer's existing brand-protection workflow* (Slack, Splunk, ServiceNow) — not a competing dashboard

For full competitive analysis with a 13-vendor feature matrix, see `07-competitive-analysis.md`. For an honest scoring against enterprise procurement requirements, see `08-enterprise-readiness.md`.

## 2. How SpoofVane fits next to existing tools

The pitch is **complement, not replace**. The typical buyer already has a primary brand-protection vendor; SpoofVane feeds that vendor's existing pipeline with results from pages it cannot otherwise reach.

| Existing tool | What it does well | What SpoofVane adds |
| --- | --- | --- |
| Netcraft / Bolster (primary brand protection) | Massive crawl, takedown relationships, 24×7 SOC | Geo-pinned + anti-bot-bypassed renders of pages they can't currently reach |
| ZeroFox / BrandShield (broad DRP) | Social media, app stores, dark web | Depth on the web-page channel specifically |
| Memcyco (in-session protection) | Real-time victim protection on the brand's own site | External view of attacker infrastructure across the open web |
| Recorded Future (threat intel) | Broad threat-actor context | Live, structured per-URL phishing evidence |

The detection output is intentionally formatted as a feed that drops into these existing workflows — Slack block-kit alerts, Splunk HEC payloads, hash-chained PDF evidence packs ready for legal review.

## 3. Users and buying centre

### Primary user — CISO / Head of Trust & Safety
Consumer-facing brands with login pages: banks, neobanks, exchanges, crypto platforms, telcos, airlines, large retailers. Anyone whose customers get phished.

### Secondary user — Brand protection teams
Inside large enterprises (P&G, Unilever) protecting against product-counterfeit and customer-deception use cases.

### Tertiary user — MSSPs
Reselling brand-protection-as-a-service into the mid-market.

### Buying centre

| Role | Function |
| --- | --- |
| **CISO** | Signs the contract; cares about brand-reputation incidents and customer-fraud loss |
| **Head of Trust & Safety** | Daily operator; cares about queue load and takedown latency |
| **Legal / DMCA team** | Consumes evidence packs for registrar takedowns |
| **SOC** | Receives IOCs via webhook into Splunk / Sentinel |

**ARR band (corrected positioning):**

| Customer profile | Realistic ARR |
| --- | --- |
| Mid-market, 1 brand, complementary to existing primary tool | $15K–$35K |
| Enterprise, 3–8 sub-brands, multi-region | $50K–$120K |
| OEM licence to a primary brand-protection vendor | $200K–$500K flat |

The original draft of this spec quoted "$40K–$300K" — that range fits primary brand-protection contracts (Netcraft, BrandShield, MarkMonitor land in $80K–$500K), not SpoofVane's complementary position. See `07-competitive-analysis.md` §7 for the bottom-up TAM derivation.

## 4. Use cases

The prototype supports these use cases directly:

1. **Login-page clone detection** — find pages anywhere on the web that visually clone the customer's real login page
2. **Payment-page clone detection** — same for checkout / billing pages, where high-value attacks concentrate
3. **Geo-targeted phishing** — render the suspect URL from the brand's target country via residential proxies; phishing pages that only render to victims in-country are caught
4. **Time-bomb phishing (concept)** — pages that look benign initially then activate on a specific date; the prototype's daily re-render + DOM-diff loop supports this, though the demo runs a single pass
5. **Pre-takedown evidence packaging** — one-click PDF export containing screenshots, DOM hash, WHOIS, hosting info, time-of-detection for the legal team and the registrar
6. **Tamper-evident audit trail** — the hash-chained inspection ledger gives downstream legal / regulator reviewers cryptographic proof the evidence has not been altered post-detection

Use cases that would belong to a fully-built version but are NOT in the prototype:

- Mobile-app store impersonation (Google Play, App Store) — discovery layer would need new sources
- Social-media impersonation (LinkedIn, X, Facebook) — different access patterns entirely
- Paid-search and SEO abuse — discovery layer extension via Bright Data SERP API
- Reverse-proxy / AiTM phishing — fundamentally a different detection model; would require an in-session SDK (Memcyco's territory)

See `07-competitive-analysis.md` §3 for the full capability matrix.

## 5. User flow

### 5.1 Brand onboarding (one-time, ~10 minutes)

1. User uploads canonical assets: login URL, payment URL, logo image, brand colour palette
2. System screenshots and DOM-hashes the canonical pages
3. System computes CLIP embedding for the logo
4. Brand record is now active in the discovery loop

### 5.2 Continuous discovery (24/7)

Three parallel feeds populate the suspect-URL queue:

- **SERP API** — branded queries phishing kits target (`"acme bank login"`, `"acme account verify"`), refreshed daily; results outside the brand's canonical domain go to inspection
- **Certificate transparency** stream — new certs containing brand-adjacent tokens
- **Newly-registered domain delta** — public TLD zone daily delta

### 5.3 Inspection (per suspect URL — the hard part)

For each suspect URL:

1. **Scraping Browser** renders the page in real Chrome from a residential IP in the brand's target country
2. **Web Unlocker** punches through anti-scanner defences
3. System captures: screenshot (full page), DOM, network requests, third-party assets, favicon hash, JS bundle hashes
4. Evidence is written to S3 with a SHA-256 content hash for tamper-evidence

### 5.4 Similarity scoring

- **Perceptual hash (pHash)** of screenshot vs canonical → visual clone score
- **Structural similarity** of DOM vs canonical → HTML clone score
- **Logo-presence detection** on a non-brand domain via CLIP embeddings
- **Favicon hash match** — exact match flag

Pages above the composite threshold proceed to AI verdict.

### 5.5 AI verdict (Claude Sonnet 4.6)

The model reasons over all signals together:

> *"This page renders the Acme logo, has a login form posting to a non-Acme domain, was registered 2 days ago, is hosted on a low-reputation ASN — high-confidence phishing."*

It produces a structured object containing:

- `verdict`: phish | suspicious | benign
- `confidence`: 0.0–1.0
- `severity`: critical | high | medium | low
- `evidence_summary`: bulleted findings
- `suggested_action`: takedown | watch | dismiss
- `takedown_draft`: registrar-specific takedown notice text

### 5.6 Action

- New alert lands in the Trust & Safety triage queue
- Pre-filled takedown request to registrar / hoster is one click away
- IOCs (domain, IP, ASN, registrar) push to the security stack (Splunk, Sentinel) via webhook
- An evidence-pack PDF is generated for legal

## 6. Scope — what's in and what's out

### In scope (prototype)

- Login-page and payment-page clone detection
- Logo / favicon similarity
- Geo-pinned rendering (single region per brand)
- AI verdict with structured output
- Triage dashboard
- Evidence-pack PDF export
- Slack webhook integration
- MCP server for Claude

### Out of scope (prototype)

- Real registrar API integration (drafts only)
- Mobile-app store scraping
- Real-time IRC / Telegram channel monitoring
- Dark-web monitoring
- Multi-region orchestration UI (the engine supports it; the UI shows one region)

## 7. Success metrics

| Metric | Target |
| --- | --- |
| Time from clone-page-live → alert | < 6 hours |
| False-positive rate after AI verdict | < 5% |
| Evidence-pack PDF generation latency | < 30 seconds |
| Takedown notice acceptance rate | > 80% (industry baseline ~60%) |

## 8. Risk register

| Risk | Mitigation |
| --- | --- |
| Adversarial-content territory — landing on illegal material during demo | Curated demo dataset; safe-browse intermediate page |
| Phishing kit operators may try to detect the inspection itself | Bright Data residential rotation, randomised user-agent / fingerprint |
| False positives erode operator trust | Two-tier scoring + AI verdict; conservative thresholds |
| Legal liability of takedown drafts | All drafts marked "draft for legal review", not auto-sent |
| Registrar integration complexity | Out of scope for prototype; webhook + PDF only |
