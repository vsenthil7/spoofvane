# SpoofVane — Analyst User Guide

**Document ID:** `SPOOFVANE-USER-GUIDE`
**Product:** SpoofVane v0.5.0 (`spoofvane-convergence-v9`)
**Coder:** Claude (Opus 4.8), running in Claude Code
**Issued:** 29 May 2026, 09:50 BST
**Audience:** SOC analysts, reviewers, brand admins, auditors, platform admins

---

## 1. What SpoofVane is

SpoofVane is an autonomous brand, executive, deepfake and fraud surface defense
platform. It continuously discovers impersonation across the web, app stores,
social media, ads and media; inspects and scores each suspect; produces an
auditable verdict; and helps you take the site down — all from one console with
court-ready evidence and a human-in-the-loop gate on every consequential action.

The console has **21 screens (P01–P21)**. This guide explains each one and how
they connect.

---

## 2. Roles (who sees what)

Navigation is role-gated. From least to most privileged:

| Role | Can do |
|------|--------|
| **viewer** | Read dashboards and settings |
| **auditor** | + Read audit log and compliance evidence |
| **reviewer** | + Approve/deny HITL actions (must differ from the analyst) |
| **analyst** | + Triage alerts, request takedowns, run discovery |
| **admin** | + Manage users, agents, cost, demo health |
| **owner** | + Manage tenants and billing |

Segregation of duties is enforced: the analyst who raises an alert cannot be the
reviewer who approves its takedown.

---

## 3. The screens, one by one

### P01 — Login
Sign in with SSO (OIDC), SAML, or local email/password. If MFA is enabled you
are challenged for a TOTP code. On success you land on the Dashboard.

### P02 — Dashboard
Your SOC overview: KPI tiles (active alerts, phish today, open takedowns, monthly
Bright Data spend), a threat-family breakdown, a region map of where suspects are
hosted, and a live pipeline strip. Starting point for the day; click any tile to
drill into the relevant queue.

### P03 — Brands
The list of brands you protect. Launch the **Brand Wizard** here to onboard a new
brand — it suggests keywords, permutation TLDs, and monitoring regions for you.

### P04 — Brand detail
Everything about one brand: canonical login/payment URLs, reference logo and
screenshot hashes, monitoring regions, and the score threshold that decides when
a suspect is escalated.

### P05 — Triage queue
The analyst work queue. Each row is a suspect with its verdict pill
(phish/suspicious/benign), composite score, source, and an SLA timer. This is
where most analyst time is spent. Click a row to open the Alert detail.

### P06 — Alert detail
The heart of the product — one suspect, ten evidence tabs:
1. **Summary** — verdict, score, brand, first seen
2. **Evidence** — screenshot, DOM, captured assets
3. **Multi-region** — how the page renders from different countries (cloaking)
4. **Verdict trace** — the model ensemble (Claude + GPT + Gemini) and any dissent
5. **MITRE** — mapped ATT&CK techniques + D3FEND countermeasures
6. **Kit** — which phishing kit matched (e.g. EvilProxy) and how
7. **Cluster** — other domains linked to this one
8. **Deepfake** — if media is involved: face/lip-sync/voiceprint/C2PA
9. **Takedown** — draft packet and submission status
10. **Audit** — the hash-chained trail for this alert

From here an analyst requests a takedown (which routes to HITL review).

### P07 — Clusters
A threat-network graph. Domains are linked when they share an ASN, registrar,
phishing kit, favicon, or TLS fingerprint — revealing campaigns rather than
isolated sites. Click a node to jump to its alert.

### P08 — Deepfakes
The deepfake review queue. Each item shows the multimodal score (face embedding,
lip-sync inconsistency, voiceprint match, and C2PA provenance) and a verdict UI
to confirm or dismiss.

### P09 — Exec protection
Executive likeness and voice monitoring — detects impersonating accounts and
cloned-voice media targeting named executives. This is a sensitive surface: it
runs under a recorded lawful basis and is gated.

### P10 — Takedowns
Multi-channel takedown status: registrar (Cloudflare/GoDaddy/Namecheap) and
hosting-abuse channels (AWS/GCP/Hetzner/OVH/Hostinger). Track reference IDs and
manually override where needed.

### P11 — Audit
The tamper-evident, hash-chained audit log with **natural-language search** — type
"analyst takedown actions for tenant acme" and it parses that into filters.

### P12 — Review queue
The HITL queue, reviewer-only. Consequential actions (takedown submission,
sensitive agent runs) wait here for approval by someone other than the analyst.

### P13 — Cost
Per-tenant Bright Data spend against the tier envelope (free/pro/business/
enterprise) with budget alerts. Shows the SLM-first routing that keeps costs down.

### P14 — Compliance
SOC 2 / ISO 27001 / DORA / NIS2 evidence and status — what auditors read.

### P15 — Admin · Agents
The agent registry with governance budgets and the **kill-switch** (global or
per-tenant) that hard-halts every running agent.

### P16 — Admin · Users
RBAC management — assign the six roles with segregation of duties.

### P17 — Admin · Tenants
Multi-tenant management, including each tenant's data-residency region.

### P18 — Admin · Demo health
Internal screen showing seed completeness and 21-page coverage status.

### P19 — Settings
Your profile, MFA enrolment, and API keys.

### P20 — Not found (404) / P21 — Forbidden (403)
Standard error screens. 403 appears when your role lacks access to a surface.

---

## 4. How the screens flow

### Primary analyst flow (detect → take down)
```
P01 Login
   ↓
P02 Dashboard ──(click a KPI tile)──► P05 Triage queue
   ↓                                     ↓ (click a suspect)
P03 Brands ──(wizard)──► P04 Brand     P06 Alert detail
   detail                                 ↓ (review the 10 tabs)
                                          ├─► P07 Clusters (see the campaign)
                                          ├─► P08 Deepfakes (if media)
                                          └─► request takedown
                                                ↓
                                          P12 Review queue (reviewer ≠ analyst approves)
                                                ↓
                                          P10 Takedowns (routed + tracked)
                                                ↓
                                          P11 Audit (every step recorded)
```

### Onboarding flow (new brand)
```
P02 Dashboard ──► P03 Brands ──(Brand Wizard)──► P04 Brand detail
   set keywords / regions / threshold ──► discovery begins ──► P05 Triage queue fills
```

### Governance / admin flow
```
P15 Admin·Agents ── set budgets, arm or fire the kill-switch
P16 Admin·Users  ── assign roles (enforce SoD)
P17 Admin·Tenants── set data-residency region per tenant
P13 Cost         ── watch Bright Data spend vs envelope
P14 Compliance   ── export auditor evidence
```

### Executive-protection flow (sensitive)
```
P09 Exec protection ── detects likeness/voice impersonation
   ↓ (any consequential action requires a named lawful basis +
      reviewer approval; egress actions also need a second authoriser)
P12 Review queue ──► P10 Takedowns ──► P11 Audit
```

### Error paths
```
Any screen, no permission ──► P21 Forbidden (403)
Unknown URL              ──► P20 Not found (404)
Incident anywhere        ──► P15 Admin·Agents → kill-switch halts all agents
```

---

## 5. Golden rules for analysts

1. **Every takedown goes through review.** You draft; a reviewer approves. This
   is by design and is audited.
2. **Sensitive surfaces (exec protection, victim-id) need a lawful basis** before
   any action — the console will block you until one is recorded.
3. **When in doubt, the verdict is "suspicious," not "phish."** The system is
   deliberately conservative and escalates dissent to a human.
4. **The kill-switch is always one click away** on Admin · Agents if anything
   looks wrong.
5. **The audit log is the source of truth.** If it isn't in the hash-chained
   audit, it didn't happen.

---

*SpoofVane Analyst User Guide — built by Claude (Opus 4.8) in Claude Code,
29 May 2026, 09:50 BST. Screens correspond to the canonical page registry
`console/src/lib/pages.ts` (P01–P21).*
