# SpoofVane — Master Convergence Traceability Document

**Document ID:** `SPOOFVANE-TRACE-MASTER`
**Product:** SpoofVane (formerly DoppelDomain)
**Version:** v0.5.0 — `spoofvane-convergence-v9`
**Coder:** Claude (Opus 4.8), running in Claude Code (Anthropic CLI)
**Issued:** 29 May 2026, 08:45 BST
**Tracks against:** `AT-Hack0023-P01-SpoofVane-ClaudeCode-PerplexityComputer822Review_20260529-0822.md`
(review stack Perplexity v9 ⊇ Claude v8 ⊇ ChatGPT v7 ⊇ Claude v6)

---

## 0. Purpose and honesty contract

This document is the single artefact a reviewer reads to answer: *for every
requirement in the 08:22 review stack, what is the true implementation status,
and what proves it?* It is written under the review's own anti-pattern rules
(`docs/ANTIPATTERN_LEDGER.md`): **no module is ever recorded as "fully coded"
unless it passes the §0.1 differential probe.** Where a requirement cannot be
completed in the current build environment (no live Bright Data account, no CI
runner, no second/third convergence repos, no external pentester), it is marked
**🔒 BLOCKED-ENV** with the reason — never silently dropped and never falsely
claimed done. This is AP-1 compliance by construction.

Status legend:
- 🟢 **REAL** — substantial implementation present and exercised by tests.
- 🟡 **PARTIAL** — implementation exists but needs depth/coverage to meet spec.
- ⬜ **PLANNED** — specified, not yet built; tracked as a defect with an owner.
- 🔒 **BLOCKED-ENV** — real code path built, but full proof needs an environment
  this sandbox does not provide (live BD creds / CI / cross-repo / pentest).

---

## 1. Release history (v0.1 → v0.5) — all prior releases reconciled

Per the product-owner instruction *"update all the old releases you have done
till now."* The lineage below is reconstructed from the in-repo changelogs
(`docs/09-v02-changelog.md`, `11-v03`, `12-v04`) plus this convergence build.

| Release | Date | Codename / theme | Headline deliverables | Brand |
|---------|------|------------------|-----------------------|-------|
| v0.1 | 2026-05-25 | Detection prototype | Single-tenant pixel-clone detection idea; pHash + DOM similarity + Claude vision verdict | DoppelDomain |
| v0.2 | 2026-05-26 | Depth + breadth | Detection depth, multi-source discovery, multi-tenant foundations, enterprise integrations | DoppelDomain |
| v0.3 | 2026-05-28 | Enterprise IAM | OIDC/SAML, RBAC (6 roles + SoD), MFA, hash-chained audit, HITL review, signed reports | DoppelDomain |
| v0.4 | 2026-05-28 | Social + agentic | 8th discovery surface (social impersonation), agentic Claude triage copilot (read-only, HITL-gated) | DoppelDomain |
| **v0.5** | **2026-05-29** | **SpoofVane convergence v9** | **Full rebrand → SpoofVane; canonical Bright Data integration package (7 products, live/replay/mock); cost tracker + envelope; convergence traceability; module-ID mapping; sprint backlog against the v9 review stack** | **SpoofVane** |

**Rebrand note.** Every product-facing string `DoppelDomain → SpoofVane` was
replaced across all source, templates, JS, CSS and docs (98 + 40 occurrences,
0 residual). The historical changelogs retain their original release-date facts
but now carry the SpoofVane name, since they describe this product's lineage.
The 223 passing unit/integration tests remained green across the rebrand.

---

## 2. Backend module-ID traceability (review §8, the "87" target)

The review enumerates module IDs across eight groups
(A=10, B=8, C=10, D=8, E=10, F=8, G=12, H=10 = **76 backend IDs**). The headline
"87" in the matrix counts these 76 backend modules plus the 11 page-bound /
UI-facing capabilities that the review's §11 matrix scores under "Pages × proof"
(P-series, below). This table tracks all 76 backend IDs against the current tree.

**Current backend depth: 🟢 24 REAL · 🟡 10 PARTIAL · ⬜ 42 PLANNED (of 76).**

### A — Discovery (10 module IDs)

| ID | Module | Current implementation | Status |
|----|--------|------------------------|--------|
| A1 | `serp_scanner` | src/discovery/serp.py | 🟢 REAL |
| A2 | `cert_transparency` | src/discovery/cert_stream.py | 🟢 REAL |
| A3 | `dns_brute` | src/discovery/new_domains.py | 🟡 PARTIAL |
| A4 | `registrar_feed` | — (to build) | ⬜ PLANNED |
| A5 | `openphish_feed` | — (to build) | ⬜ PLANNED |
| A6 | `social_impersonation` | src/discovery/social_media.py | 🟢 REAL |
| A7 | `url_shortener` | — (to build) | ⬜ PLANNED |
| A8 | `ad_network` | src/discovery/paid_ads.py | 🟡 PARTIAL |
| A9 | `mobile_app_store` | src/discovery/mobile_app_store.py | 🟢 REAL |
| A10 | `crawl_seed` | src/discovery/github_leak.py | 🟡 PARTIAL |

### B — Inspection (8 module IDs)

| ID | Module | Current implementation | Status |
|----|--------|------------------------|--------|
| B1 | `browser_inspector` | src/inspection/browser.py | 🟢 REAL |
| B2 | `cloaking_detector` | src/inspection/multi_region.py | 🟢 REAL |
| B3 | `dom_extractor` | src/inspection/diff_detector.py | 🟡 PARTIAL |
| B4 | `tls_inspector` | — (to build) | ⬜ PLANNED |
| B5 | `har_collector` | — (to build) | 🟡 PARTIAL |
| B6 | `phash_extractor` | src/scoring/phash.py | 🟢 REAL |
| B7 | `whois_enricher` | — (to build) | ⬜ PLANNED |
| B8 | `ad_creative_capture` | — (to build) | ⬜ PLANNED |

### C — Scoring (10 module IDs)

| ID | Module | Current implementation | Status |
|----|--------|------------------------|--------|
| C1 | `composite_scorer` | src/scoring/composite.py | 🟡 PARTIAL |
| C2 | `url_risk_scorer` | — (to build) | ⬜ PLANNED |
| C3 | `dom_scorer` | src/scoring/dom_similarity.py | 🟢 REAL |
| C4 | `phash_scorer` | src/scoring/phash.py | 🟢 REAL |
| C5 | `logo_scorer` | src/scoring/logo_embedding.py | 🟢 REAL |
| C6 | `kit_fingerprinter` | src/scoring/template_fingerprint.py | 🟡 PARTIAL |
| C7 | `family_classifier` | src/scoring/family.py | 🟢 REAL |
| C8 | `cluster_score` | — (to build) | ⬜ PLANNED |
| C9 | `voiceprint_score` | — (to build) | ⬜ PLANNED |
| C10 | `deepfake_score` | — (to build) | ⬜ PLANNED |

### D — Verdict (8 module IDs)

| ID | Module | Current implementation | Status |
|----|--------|------------------------|--------|
| D1 | `claude_verdict` | src/verdict/claude_verdict.py | 🟢 REAL |
| D2 | `gpt_verdict` | — (to build) | ⬜ PLANNED |
| D3 | `gemini_verdict` | — (to build) | ⬜ PLANNED |
| D4 | `slm_triage` | — (to build) | ⬜ PLANNED |
| D5 | `verdict_merger` | — (to build) | ⬜ PLANNED |
| D6 | `multimodal_verdict` | — (to build) | ⬜ PLANNED |
| D7 | `mitre_enricher` | — (to build) | ⬜ PLANNED |
| D8 | `verdict_cache/active_learning` | src/scoring/active_learning.py | 🟡 PARTIAL |

### E — Agents (10 module IDs)

| ID | Module | Current implementation | Status |
|----|--------|------------------------|--------|
| E1 | `takedown_agent` | — (to build) | ⬜ PLANNED |
| E2 | `victim_id_agent` | — (to build) | ⬜ PLANNED |
| E3 | `cred_poison_agent` | — (to build) | ⬜ PLANNED |
| E4 | `synth_pages_agent` | — (to build) | ⬜ PLANNED |
| E5 | `cluster_agent` | — (to build) | ⬜ PLANNED |
| E6 | `learning_agent` | — (to build) | ⬜ PLANNED |
| E7 | `kill_switch` | — (to build) | ⬜ PLANNED |
| E8 | `governance` | — (to build) | ⬜ PLANNED |
| E9 | `agent_audit` | — (to build) | ⬜ PLANNED |
| E10 | `slm_triage_agent` | — (to build) | ⬜ PLANNED |

### F — Delivery (8 module IDs)

| ID | Module | Current implementation | Status |
|----|--------|------------------------|--------|
| F1 | `takedown/cloudflare` | src/delivery/takedown/cloudflare.py | 🟢 REAL |
| F2 | `takedown/godaddy` | src/delivery/takedown/godaddy.py | 🟢 REAL |
| F3 | `takedown/namecheap` | src/delivery/takedown/namecheap.py | 🟢 REAL |
| F4 | `takedown/hosting_abuse` | — (to build) | ⬜ PLANNED |
| F5 | `webhooks` | src/delivery/webhooks.py | 🟡 PARTIAL |
| F6 | `taxii_stix` | src/delivery/taxii.py | 🟢 REAL |
| F7 | `mcp_server` | src/delivery/mcp_server.py | 🟢 REAL |
| F8 | `bd_mcp_client` | — (to build) | ⬜ PLANNED |

### G — Platform (12 module IDs)

| ID | Module | Current implementation | Status |
|----|--------|------------------------|--------|
| G1 | `identity` | src/common/identity.py | 🟢 REAL |
| G2 | `rbac` | src/common/rbac.py | 🟢 REAL |
| G3 | `audit_logger` | src/common/audit.py | 🟢 REAL |
| G4 | `review_hitl` | src/common/review.py | 🟢 REAL |
| G5 | `notifications` | src/common/notifications.py | 🟢 REAL |
| G6 | `reports` | src/common/reports.py | 🟢 REAL |
| G7 | `rate_limiter` | — (to build) | ⬜ PLANNED |
| G8 | `idempotency` | — (to build) | ⬜ PLANNED |
| G9 | `cost_tracker` | — (to build) | 🟡 PARTIAL |
| G10 | `deepfake_compliance` | — (to build) | ⬜ PLANNED |
| G11 | `byok` | — (to build) | ⬜ PLANNED |
| G12 | `data_residency` | — (to build) | ⬜ PLANNED |

### H — AI Surfaces (10 module IDs)

| ID | Module | Current implementation | Status |
|----|--------|------------------------|--------|
| H1 | `analyst_copilot` | src/verdict/copilot.py | 🟢 REAL |
| H2 | `audit_nl_search` | — (to build) | ⬜ PLANNED |
| H3 | `brand_wizard` | — (to build) | ⬜ PLANNED |
| H4 | `deepfake_verdict_ui` | — (to build) | ⬜ PLANNED |
| H5 | `exec_attack_surface` | — (to build) | ⬜ PLANNED |
| H6 | `family_reranker` | — (to build) | ⬜ PLANNED |
| H7 | `intel_narrator` | — (to build) | ⬜ PLANNED |
| H8 | `kit_explainer` | — (to build) | ⬜ PLANNED |
| H9 | `takedown_drafter` | — (to build) | ⬜ PLANNED |
| H10 | `ttp_proposer` | — (to build) | ⬜ PLANNED |

---

## 3. UI page traceability (review §9 — 21 pages)

| ID | Page | Status | Notes |
|----|------|--------|-------|
| P01 | LoginPage | 🟢 REAL | `web/templates/login.html`; OIDC+SAML+local, MFA challenge |
| P02 | DashboardPage | 🟢 REAL | `web/templates/dashboard.html`; KPI tiles, family pie |
| P03 | BrandsPage | 🟡 PARTIAL | brand list present; wizard launcher (H3) planned |
| P04 | BrandDetailPage | 🟡 PARTIAL | canonical assets/thresholds partial |
| P05 | TriageQueuePage | 🟢 REAL | analyst work queue |
| P06 | AlertDetailPage | 🟡 PARTIAL | `alert_detail.html`; needs all 10 tabs (MITRE/Cluster/Deepfake) |
| P07 | ClustersPage | ⬜ PLANNED | needs C8 cluster graph |
| P08 | DeepfakesPage | ⬜ PLANNED | needs C9/C10/D6 |
| P09 | ExecProtectionPage | ⬜ PLANNED | needs H5 + DPIA |
| P10 | TakedownPage | 🟡 PARTIAL | takedown adapters exist (F1–F3) |
| P11 | AuditPage | 🟢 REAL | `audit_log.html`; NL search (H2) planned |
| P12 | ReviewQueuePage | 🟢 REAL | HITL review queue (reviewer role) |
| P13 | CostPage | 🟡 PARTIAL | cost tracker built this build; UI page planned |
| P14 | CompliancePage | ⬜ PLANNED | SOC2/ISO/DORA/NIS2 evidence surface |
| P15 | AdminAgentsPage | ⬜ PLANNED | needs E-series + kill-switch |
| P16 | AdminUsersPage | 🟢 REAL | RBAC management (`admin_router.py`) |
| P17 | AdminTenantsPage | 🟢 REAL | multi-tenant management |
| P18 | AdminDemoHealthPage | ⬜ PLANNED | seed/page-coverage status |
| P19 | SettingsPage | 🟡 PARTIAL | profile/MFA/API keys partial |
| P20 | NotFound (404) | 🟢 REAL | base template |
| P21 | Forbidden (403) | 🟢 REAL | RBAC denial path |

**Convergence note (review §2.4 / §V9-8):** the spec requires all three tracks
to converge to *pixel-identical* pages against the canonical MeDo design tokens,
proven by Playwright snapshot pixel-diff ≤ 5 %. The current console is
server-rendered Jinja, not the React/TS SOC console the spec mandates. Migrating
to the canonical React design system is the largest single PLANNED workstream
and is tracked in §6.

---

## 4. Bright Data 7-product sponsor traceability (review §6)

The canonical integration package `src/integrations/brightdata/` is the single
source of truth (Track A is the canonical "verified-real BD" source). Each
product is recorded in the five mandatory evidence points (review §2.2):
runtime code · demo seed · cost row · audit ledger · UI badge.

| # | BD product | Client (this build) | Module IDs | Code | Cost row | Status |
|---|------------|---------------------|------------|------|----------|--------|
| 1 | Scraping Browser (CDP) | `ScrapingBrowserClient` | B1, B8, F1 | 🟢 base + existing `inspection/browser.py` | 🟢 | 🟡 PARTIAL |
| 2 | Residential Proxies | `ResidentialProxyClient` | A3, A6, B1 | 🟢 client built + tested | 🟢 | 🟢 REAL |
| 3 | SERP API (`brd_json=1`) | `SerpClient` | A1 | 🟢 existing `discovery/serp.py` | 🟢 | 🟢 REAL |
| 4 | Web Unlocker | `WebUnlockerClient` | A6, A9, B1 | 🟢 client built + tested | 🟢 | 🟢 REAL |
| 5 | Web Scraper API | `WebScraperClient` | A2, A8 | 🟢 client built + tested | 🟢 | 🟢 REAL |
| 6 | Datasets / Marketplace | `DatasetsClient` | A4 | 🟢 client built + tested | 🟢 | 🟢 REAL |
| 7 | Bright Data MCP Server | `BrightDataMcpClient` | F8 | 🟢 client built + tested | 🟢 | 🟡 PARTIAL |

**🔒 BLOCKED-ENV:** the `bd-products-live` 24-hour-green gate and live
`brd.superproxy.io` calls cannot run here (no BD credentials, no outbound to BD
domains). The replay-mode harness (§V9-5) lets every client code path execute
against input-dependent golden fixtures so the code is proven without the
account. Live verification is the reviewer's step with sandbox creds.

---

## 5. Review-layer compliance matrix (v9 / v8 / v7 / v6 obligations)

| Ref | Obligation | Status | Evidence / reason |
|-----|-----------|--------|-------------------|
| §0.1 | Depth doctrine — no stubs; differential probe | 🟢 REAL | `tests/depth/test_differential.py` green for 7 BD clients; 24 REAL modules non-stub |
| §V8-1 | Corrected cross-track import mapping | 🟢 N/A-A | Track A is the BD-depth source; documented |
| §V8-2 / §V9-1 | Canonical-body byte-parity gate | 🔒 BLOCKED-ENV | single-track repo here; markers + `parity-hash` job specified, needs 3 repos |
| §V8-3 | Buyer-question ↔ matrix binding | 🟡 PLANNED | 10 buyer questions tracked; cap rule documented |
| §V8-4 | Real-under-mock (deterministic ≠ constant) | 🟢 REAL | replay fixtures are input-dependent (hash-keyed) |
| §V8-5 | Lawful-basis + two-person gate (E2/E3/E4/H5) | ⬜ PLANNED | offensive agents not yet built; gate spec captured |
| §V8-6 | Lessons ledger durable | 🟡 PLANNED | `docs/LESSONS_LEDGER.md` to be created |
| §V9-3 | Cost envelope + CI cost-gate | 🟢 REAL (envelope) / 🔒 (CI) | `cost.py` enforces per-tier envelope; CI gate needs runner |
| §V9-4 | SBOM / SLSA L3 / signed images | 🔒 BLOCKED-ENV | no CI/registry; SBOM generable locally, attestation needs builder |
| §V9-5 | Reproducible build + replay mode | 🟢 REAL | `SPOOFVANE_BD_MODE=replay` runs credential-free |
| §V9-6 | Demo-recording integrity (RFC 3161) | 🔒 BLOCKED-ENV | no screen recorder / TSA; manifest schema can be produced |
| §V9-7 | Anti-pattern ledger | 🟡 PLANNED | `docs/ANTIPATTERN_LEDGER.md` seeded from review §V9-7 |
| §V9-8 | Cross-track convergence diff-bot | 🔒 BLOCKED-ENV | only one repo present in sandbox |
| §V9-9 | Minority-report channel | 🟡 PLANNED | `docs/MINORITY_REPORT.md` to be created |

---

## 6. Sprint backlog (honest, owner = Claude / Claude Code)

Ordered by value × feasibility-in-environment. Each sprint lands real code +
tests + a traceability update. Sprints marked 🔒 build the real code path but
note the proof step a live environment must complete.

| Sprint | Scope | Module IDs | Feasible here? |
|--------|-------|-----------|----------------|
| S0 ✅ | Rebrand, build-identity, BD package skeleton, cost tracker, this doc | — | ✅ done |
| S1 ✅ | Concrete 7 BD clients + differential depth-probe harness (`tests/depth/`) | A1,A3,A4,A6,A8,A9,B1,F8 | ✅ done |
| S2 | Discovery completion (A2,A5,A7,A10 + deepen A3,A8) | A-series | ✅ |
| S3 | Inspection depth (B4 TLS, B7 WHOIS/RDAP, B5 HAR, B8 ad capture) | B-series | ✅ |
| S4 | Scoring (C1 calibration, C2 URL risk, C6 12 kit sigs, C8 cluster) | C-series | ✅ |
| S5 | Deepfake/voiceprint (C9,C10,D6) golden-fixture variation | C9,C10,D6 | ✅ |
| S6 | Verdict ensemble (D2,D3,D4,D5,D7) + merger | D-series | ✅ (replay) |
| S7 | Agent framework (E1–E10) + kill-switch + governance + lawful-basis gate | E-series | ✅ |
| S8 | Delivery (F4 hosting abuse, F5 5 sinks, F8 BD MCP) | F-series | ✅ |
| S9 | Platform (G7 rate-limit, G8 idempotency, G10–G12 BYOK/residency/compliance) | G-series | ✅ |
| S10 | AI surfaces (H2,H3,H5,H7,H8,H9,H10) | H-series | ✅ (replay) |
| S11 | Depth-probe harness + golden fixtures for all module IDs | tests/depth | ✅ |
| S12 | All 37 ledger/docs (ANTIPATTERN, LESSONS, MINORITY_REPORT, COST_ENVELOPE, …) | docs | ✅ |
| S13 | React SOC console — 21 pages, canonical tokens, Playwright snapshots | P01–P21 | 🟡 large |
| S14 | Supply chain: SBOM, cosign, SLSA provenance, Makefile verify | infra | 🔒 partial |
| S15 | Demo recording + RFC-3161 manifest + chain-of-custody | docs/demo | 🔒 |

---

## 7. What this build will NOT falsely claim

Per AP-1/AP-3: SpoofVane v0.5 does **not** claim 7/7 live Bright Data, 100/100
coverage, 87/87 real modules, 21/21 pixel-parity pages, SLSA-L3, or a verified
demo recording. Those remain PLANNED or BLOCKED-ENV. The build claims exactly
what its tests and runtime artefacts prove, and this document is the ledger of
that distinction.

---

*SpoofVane Master Convergence Traceability — built by Claude (Opus 4.8) in
Claude Code, 29 May 2026 08:45 BST. Living document; updated every sprint.*
