# 07 — Competitive Analysis & Market Position

**Status:** Honest assessment, May 2026. Authored after competitive research, not pitched.

This document is deliberately written against my own product. Every claim I'd be tempted to make about a "novel moat" is checked against what incumbents already do. Where the moat shrinks, I say so. The goal is to land on a positioning that survives a sceptical buyer call — not one that survives only a friendly hackathon judge.

---

## 1. The honest summary

DoppelDomain as built today is **not** an enterprise-grade brand-protection platform, and it should not pitch as one. Three of the four capabilities the original spec claimed as differentiators are already in production at incumbents.

What is genuinely defensible — and what the product should be positioned around — is a much narrower wedge:

> **The geo-targeted phishing-infrastructure detector that reaches pages incumbents can't.**
> 
> Existing brand-protection tools struggle with phishing pages that are Cloudflare-fronted, geo-restricted to the victim's country, JS-rendered, or behind aggressive anti-bot defences. Bright Data's residential proxies + Scraping Browser are the enabling technology to reach those pages reliably and at scale. DoppelDomain is the layer that captures, fingerprints, and routes them.

This is an **add-on** product positioned alongside Netcraft / ZeroFox / BrandShield, not a replacement for them. Realistic ARR: $30–80K per enterprise customer as a complementary feed; not $300K as a primary brand-protection contract.

The hackathon version demonstrates the core thesis. Section 5 lays out what's missing for production.

---

## 2. Competitive landscape

The brand-impersonation and digital-risk-protection (DRP) market in 2026 contains four distinguishable archetypes, each with multiple vendors. We position against the first three; the fourth is adjacent.

| Archetype | Detection model | Representative vendors | Where they're strong | Where they're weak |
|---|---|---|---|---|
| **A. External infrastructure monitors** | Crawl the open web + cert-transparency + DNS, detect look-alike domains and clone pages | Netcraft, ZeroFox, BrandShield, Bolster | Scale, takedown relationships, breadth across social/app stores | Geo-blocked + anti-bot pages; speed-to-detect on first-hour attacks |
| **B. In-session / browser-side defenders** | JavaScript on the protected brand's site detects when a victim is being phished and acts in real time | Memcyco | Stops attacks in flight; per-victim visibility; defeats reverse-proxy phishing | Requires JS on the brand's own pages; doesn't see attacks against brands they don't have code on |
| **C. IP / domain-portfolio specialists** | Trademark watch + UDRP + registrar relationships | MarkMonitor, Corsearch, OpSec, Red Points | Legal teeth, mature enforcement pipelines | Slow; mostly post-hoc; less technical depth on detection |
| **D. Digital risk protection (broad)** | Multi-source threat intel (dark web, credentials, social, brand) | Recorded Future, CrowdStrike Falcon Intel, Constella, Cyble | Breadth; SOC integration; threat-actor context | Brand-impersonation is one of many features, not the focus |

DoppelDomain plays in **A** — external infrastructure monitoring. It is **not** an alternative to Memcyco (B), which solves a fundamentally different problem at a different layer.

---

## 3. Feature matrix: 13 vendors × 14 capabilities

This is the matrix a CISO would actually use when evaluating. Filled honestly — `✓` means in production today, `~` means partial or via partner, `✗` means not offered.

| Capability | **DoppelDomain (today)** | **DoppelDomain (12-mo roadmap)** | Netcraft | ZeroFox | BrandShield | Bolster | Recorded Future | MarkMonitor | Memcyco | Red Points | Corsearch | Cyble | Constella | BrandIntel (PhishLabs) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Look-alike domain detection (typosquats, IDN, combo) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Certificate-transparency monitoring | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ~ | ~ | ✓ | ✓ | ✓ |
| **Headless-browser page rendering** | ✓ | ✓ | ✓ | ~ | ~ | ✓ | ~ | ~ | n/a | ~ | ~ | ~ | ~ | ✓ |
| **Screenshot / pHash visual similarity** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ~ | n/a | ✓ | ~ | ~ | ~ | ✓ |
| **DOM-structural similarity** | ✓ | ✓ | ~ | ~ | ~ | ~ | ✗ | ✗ | n/a | ~ | ✗ | ✗ | ✗ | ~ |
| **Geo-pinned rendering (residential)** | **✓** | **✓** | ~ | ✗ | ✗ | ~ | ✗ | ✗ | n/a | ✗ | ✗ | ✗ | ✗ | ~ |
| **Anti-bot bypass at inspection time** | **✓** | **✓** | ~ | ✗ | ✗ | ~ | ✗ | ✗ | n/a | ✗ | ✗ | ✗ | ✗ | ~ |
| Mobile-app store impersonation | ✗ | ~ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✗ | ✓ | ✓ | ~ | ~ | ✓ |
| Social-media impersonation | ~ | ✓ | ~ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Paid-ad / search-engine abuse | ✗ | ~ | ~ | ✓ | ✓ | ~ | ✓ | ✓ | ~ | ✓ | ~ | ~ | ~ | ✓ |
| Dark-web / leaked credential monitoring | ✗ | ✗ | ~ | ✓ | ~ | ~ | ✓ | ~ | ~ | ~ | ~ | ✓ | ✓ | ✓ |
| **Real-time in-session victim protection** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** | ✗ | ✗ | ✗ | ✗ | ✗ |
| Automated takedown with registrar relationships | ✗ | ~ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ |
| SOC / 24×7 analyst service | ✗ | ✗ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ~ | ✓ | ✓ | ✓ | ✓ | ✓ |

Columns where DoppelDomain shows **bold** wins are the genuine wedge. Everything else is either parity (table stakes) or a gap (sections 4–5).

---

## 4. Where DoppelDomain is genuinely differentiated

Three capabilities, all of them downstream of the Bright Data stack:

### 4.1 Geo-pinned residential rendering

**Why it matters.** Modern phishing kits route based on the victim's geo. A phishing page targeting US Chase customers will serve clean content to a UK IP and the clone to a US residential IP. External scanners that crawl from datacentre IPs *cannot see the phish*. Netcraft has some residential proxy coverage, but their public materials describe screenshot analysis, not country-pinned rendering as a core capability. Most competitors don't claim it at all.

**How we do it.** Bright Data residential proxies, pinned per-brand to the `target_country` on the Brand record. The Scraping Browser session traverses CDP with the proxy in the loop, so the rendered DOM is what a real local victim sees.

### 4.2 Anti-bot bypass at inspection time

**Why it matters.** Phishing infrastructure increasingly fronts behind Cloudflare, Akamai, hCaptcha, and JS challenges, partly *because* it defeats brand-protection scanners. A scanner that gets a 403 cannot fingerprint. Bright Data Web Unlocker handles the challenge response; the rendered output flows into the same pHash/DOM scoring path.

**Trade-off honestly stated.** This is a Bright Data dependency, not our IP. The wedge here is "we know how to wire it up well for this use case," not "we invented the bypass."

### 4.3 Hash-chained evidence ledger

**Why it matters.** When a brand goes to a registrar, hoster, or law-enforcement contact, the question is "can you prove the page was in this state at this time?" Most tools produce a screenshot and a timestamp. We produce a SHA-256 hash chain across every inspection, so any post-hoc tampering with the evidence is detectable. This isn't unique technology — it's a standard tamper-evidence pattern — but it's a saleable feature most brand-protection tools omit.

---

## 5. Where DoppelDomain is *not* enterprise-ready

Being honest about this matters more than being honest about strengths. A buyer call collapses on the gaps below within ten minutes.

### 5.1 Detection gaps

- **Single-channel.** Web pages only. No social-media impersonation (LinkedIn, X, Facebook, Instagram), no mobile-app stores (Google Play, App Store, regional stores), no paid-search abuse, no email-domain spoofing, no executive impersonation, no dark-web credential monitoring. Real enterprises buy a platform, not a feed.
- **No customer-side telemetry.** We don't see traffic patterns on the brand's own site, so we cannot detect reverse-proxy phishing (Modlishka, EvilProxy, Frappo) that bypasses domain-based detection entirely. Memcyco does. This is a different architecture; we can't bolt it on without an SDK on the brand's site.
- **Discovery breadth.** Three sources (SERP, cert-transparency, newly-registered domains) is a starting point. Production tools also crawl Tranco / Majestic, Telegram / Discord phishing-kit marketplaces, paste sites, public S3 buckets, GitHub leaks, and 100+ regional ccTLD zone files. Each adds engineering and licensing cost.

### 5.2 Enforcement gaps

- **No registrar relationships.** A takedown notice is only as fast as the relationship. Netcraft has direct API-level relationships with major registrars/hosters; MarkMonitor has 20+ years of them. We produce a PDF draft addressed to a registrar — a human still has to send it and chase it.
- **No SOC.** Enterprises increasingly buy outcomes, not tools: "remove the phish in <2h, 24/7, SLA-backed." We have no analyst team, no rota, no SLA, no incident-bridge process. This is also expensive to build (~10–15 FTEs minimum for global coverage).
- **No legal workflow.** No DMCA submission portal integration, no UDRP filing assistance, no chain-of-custody export to legal counsel.

### 5.3 Platform gaps

- **No multi-tenancy.** The current schema is single-tenant. Brand-protection vendors run thousands of brands on one platform; we'd need RBAC, per-tenant rate limits, per-tenant evidence-segregation, regional data residency (EU vs US vs APAC).
- **No SSO.** SAML/OIDC + SCIM provisioning are RFP table stakes.
- **No enterprise integrations.** Splunk HEC and Slack webhooks are stubs. We'd need first-class connectors to: ServiceNow, Jira, PagerDuty, Microsoft Sentinel, Chronicle, Cortex XSOAR, Tines, Torq, Cribl, plus the major SIEMs' native parsers.
- **No audit log surface.** The hash-chained inspections are tamper-evident, but there's no admin audit log (who triaged what, who exported what, who changed thresholds).
- **No regulatory posture.** No SOC 2 Type II, no ISO 27001, no GDPR DPA template, no HIPAA BAA. Without at least SOC 2 you don't pass procurement at a Fortune 1000.

### 5.4 Operational gaps

- **Scoring is single-tier and tunable per-brand only.** Production tools learn per-attack-family scoring (Microsoft 365 phish kits, banking phish kits, crypto wallet phish kits) and per-victim-industry models.
- **No active-learning loop.** Analyst triage outcomes (false positive vs. true positive) should feed back into scoring weights and verdict-engine fine-tuning. Today nothing reads `AlertStatus`.
- **No cost-tracking.** Web Unlocker and Scraping Browser sessions are not free; an enterprise tenant inspecting 10K URLs/day will rack up real Bright Data spend. There's no per-tenant budget cap or cost-attribution surface.

---

## 6. Direct vendor head-to-heads

How to position against the three most likely "but we already use X" objections.

### vs. Netcraft

| | Netcraft | DoppelDomain |
|---|---|---|
| Scale | 20+ years, massive crawl footprint | New entrant |
| Takedown speed | Industry-leading registrar relationships | Draft only, manual send |
| Geo-pinned rendering | Partial (datacentre-heavy) | Native (residential per-brand) |
| Anti-bot reach | Partial | Native (Web Unlocker) |
| Evidence packaging | Screenshot + URL | Hash-chained evidence pack + DOM excerpt + ASN/registrar context |
| Best for | Primary brand-protection contract | **Augmenting Netcraft on hard-to-reach pages** |

**Pitch:** "Netcraft handles the easy 80%. We feed them the hard 20%: geo-blocked, Cloudflare-fronted, anti-bot-protected pages they're not seeing today. Same evidence format, same takedown workflow on your side."

### vs. ZeroFox

| | ZeroFox | DoppelDomain |
|---|---|---|
| Coverage | Social, app stores, dark web, brand impersonation | Web pages only |
| Detection model | URL/keyword/asset matching | Page-content fingerprinting |
| Detection-time visibility | Discovery-first | Rendered-page-first |
| Best for | Multi-channel brand-protection programme | **Phishing-infrastructure depth on the web channel** |

**Pitch:** ZeroFox covers breadth. We add depth on the one channel where brand-impersonation losses are largest — credential-harvesting web pages targeting your login flows.

### vs. Memcyco

This is the most important head-to-head because Memcyco is the most technically advanced player and the easiest one to confuse us with.

| | Memcyco | DoppelDomain |
|---|---|---|
| Where the detection runs | JavaScript on the *protected brand's* site | External scanner |
| What it sees | Real victims being phished in real time | Phishing infrastructure once it's live |
| When it sees it | At victim interaction | At discovery (typically minutes to hours after go-live) |
| What it defeats | Reverse-proxy phishing, AiTM | Static / semi-dynamic clones |
| Deployment | Requires JS on every brand login page | Agentless |
| Best for | Protecting users on YOUR site, in session | Detecting phishing infrastructure across the open web |

**Pitch:** Memcyco protects users on your own site. We tell you what infrastructure exists across the open web targeting your brand. **Buy both — they solve adjacent problems.**

---

## 7. Realistic market sizing and pricing

The original spec quoted "$40K–$300K ARR per enterprise customer." That range is correct for primary brand-protection contracts (Netcraft, BrandShield, MarkMonitor land in $80K–$500K). It is **wrong** for DoppelDomain in its current scope.

Honest ARR bands for the wedge described above:

| Customer profile | Realistic ARR band | Notes |
|---|---|---|
| Mid-market fintech / crypto exchange / neobank, 1 brand, 1 login surface | **$15K–$35K** | Add-on to existing Netcraft / Bolster contract; budget comes from CISO discretionary or T&S |
| Enterprise bank / global retailer, 3–8 sub-brands, multi-region | **$50K–$120K** | Per-brand pricing with volume discount; sold into the same team that runs the primary contract |
| Brand-protection vendor reselling DoppelDomain as an OEM "hard-to-reach pages" feed | **$200K–$500K** flat | This is the most credible 7-figure ARR path: licence the engine to one of the big platforms, not sell direct |

Bottom-up TAM check, using publicly known counts:

- ~5,000 enterprises globally that buy primary brand protection at $80K+ today
- Of those, ~1,500 have international login surfaces (banks, exchanges, airlines, telcos, retailers, crypto, SaaS)
- 30% conversion to a $40K add-on = **~$18M ARR realistic ceiling as a direct-sales product over 5 years**
- Plus 2–3 OEM deals at $300K each = **~$1M ARR via licence** — this is where it gets interesting

The OEM path is where this product gets to enterprise-grade *quickly*, because the partner brings the SOC, takedown, and SOC 2 you don't have.

---

## 8. The 12-month path to "enterprise-grade"

If the team wanted to take this beyond hackathon and to a sellable product, here's the realistic ordering. The estimates are honest engineer-months at a small team (3–5 engineers).

### Quarter 1 — make the wedge undeniable
- Multi-tenant data model with per-tenant evidence segregation
- SSO (SAML + OIDC) and SCIM provisioning
- SOC 2 Type I (start the audit — Type II requires 6+ months of evidence)
- Bright Data cost-attribution + per-tenant budget caps
- First-class integrations: Splunk, Microsoft Sentinel, Chronicle, ServiceNow, Jira, PagerDuty

### Quarter 2 — close the most expensive detection gap
- Mobile-app store impersonation (Google Play, App Store, F-Droid, regional Android stores)
- Paid-search abuse detection (Bright Data SERP API + ad-rendering)
- Active-learning loop from analyst triage back to scoring weights
- Per-attack-family scoring profiles (M365 kit, banking kit, crypto kit, etc.)

### Quarter 3 — earn the takedown story
- Direct API integration with the top 5 registrars (GoDaddy, Namecheap, PorkBun, Cloudflare Registrar, Tucows)
- Direct API integration with major hosters (Cloudflare, Hostinger, Hetzner, OVH, AWS abuse, GCP abuse)
- DMCA submission automation
- 8×5 analyst-supported tier (small in-house team, not a full SOC)
- SOC 2 Type II achieved

### Quarter 4 — make the OEM pitch
- Whitelabel mode for resale by Netcraft / BrandShield / Bolster
- Per-OEM evidence pack templates
- High-volume mode (10K+ URLs/day per tenant)
- Public benchmark vs. a published phishing dataset (PhishTank, OpenPhish) — this is what the OEM partner will diligence

After this, the product can credibly walk into a Fortune 1000 procurement department.

---

## 9. Risks to the thesis

Three things would invalidate the positioning above:

1. **Netcraft / Bolster ships geo-pinned residential rendering as a core capability** — they have the engineering and the relationships. Estimated probability: 40% over 24 months. Mitigation: depth in DOM-structural similarity + per-attack-family scoring, where they are weaker.

2. **Bright Data prices the residential proxy + Web Unlocker stack such that unit economics don't work for sub-$100K ARR customers.** This is the single biggest commercial risk and we should model it explicitly. Mitigation: cap inspection rate per-tenant, tier pricing on inspections-per-month not URLs-watched.

3. **Reverse-proxy phishing (Memcyco's wedge) becomes the dominant attack pattern**, making external scanning structurally less valuable. Estimated probability: 30% over 36 months. Mitigation: partner with Memcyco rather than compete; the products are complementary.

---

## 10. What this means for the hackathon submission

For the hackathon judges, **do not pitch this as a category killer**. The judges read 50 submissions a week; they recognise "we beat $300K incumbents" as wishful thinking on sight.

Pitch instead:

> *"Bright Data's residential proxy + Scraping Browser + Web Unlocker stack is uniquely good at reaching phishing pages that incumbents miss. We've packaged that into a working detector with a hash-chained evidence ledger and a Claude-powered verdict engine. It's not a Netcraft replacement — it's a feed that makes Netcraft and friends substantially better."*

That story is **defensible under questioning**, demos beautifully (geo-pinned rendering is a striking live demo), and earns the technical-application points the Bright Data rubric weights heavily — without trying to bluff the business-value points the product doesn't yet deserve.

---

*End of competitive analysis.*
