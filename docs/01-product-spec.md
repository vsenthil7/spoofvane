# DoppelDomain — Product Specification

**Document:** 01 — Product Spec
**Version:** 0.1 (hackathon prototype)
**Date:** 28 May 2026

---

## 1. Problem statement

Brand impersonation is now the #1 entry vector for credential-theft and customer-defrauding attacks. Existing brand-protection tools (Recorded Future Brand Intelligence, ZeroFox, BrandShield) catch the obvious cases — typosquats of `acme.com` such as `acmme.com`, or domains containing the literal brand string. Attackers know this and moved on.

### Modern phishing infrastructure profile

- Uses **unrelated-looking domains** (`account-update-portal[.]xyz`) with no brand string
- Hosts a **pixel-perfect clone** of the victim's login page, often scraped from the real site that morning
- Sits behind **Cloudflare and aggressive bot detection** — security scanners receive a 403 or a JS challenge, not the actual phishing page
- Rotates IPs and domains on a **48-hour cycle**
- **Geo-targets**: the phishing payload only renders when the visitor's IP is in the victim country

The signal almost nobody monitors at scale is **the rendered page DOM itself**. If a page anywhere on the open web is a near-pixel clone of your real login page, that is the phishing site — regardless of what the domain string looks like.

You cannot do this without:

1. The ability to **render JS-heavy adversarial pages** (real Chrome, not a curl)
2. **Geo-distributed access** (residential IPs in the victim country)
3. **Bypass of bot defences** that phishing kits put up *specifically to evade security scanners*

This is exactly the capability Bright Data's Scraping Browser + Web Unlocker were built for.

## 2. Why this hasn't been solved already

| Current approach | Why it fails |
| --- | --- |
| DNS / certificate-transparency monitoring | Catches typosquats; misses unrelated-looking domains |
| Brand-keyword Google Alerts | Useless for domains that don't contain the brand name |
| Standard brand-protection vendors | Crawl-based — phishing kits actively block crawlers; geo-targeted pages never render |
| Manual takedown teams | Reactive — a customer reports the phishing page after being scammed |
| URLScan / PhishTank | Crowd-sourced; latency hours-to-days; coverage spotty |

The novel angle: **visually-similar / DOM-similar page detection across the open web, with the access stack to actually reach the adversarial pages.**

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

**ARR band:** $40K–$300K depending on brand portfolio size and region count.

## 4. Use cases

1. **Login-page clone detection** — find pages anywhere on the web that visually clone the customer's real login page
2. **Payment-page clone detection** — same for checkout / billing pages, where high-value attacks concentrate
3. **Mobile-app store impersonation** — fake Android APK landing pages distributing trojanised apps
4. **Geo-targeted phishing** — render the suspect URL from 5 regions; flag URLs that show the phishing payload only in some
5. **Time-bomb phishing** — pages that look benign initially then activate on a specific date, detected by daily re-render and DOM diff
6. **Pre-takedown evidence packaging** — one-click PDF export containing screenshots, DOM hash, WHOIS, hosting info, time-of-detection for the legal team and the registrar

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
