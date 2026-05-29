# DoppelDomain v0.2 — what changed

Where v0.1 was a single-tenant prototype that demonstrated the detection idea, v0.2 closes the most-asked-for gaps from the [enterprise readiness analysis](08-enterprise-readiness.md) — detection depth, discovery breadth, multi-tenant platform foundations, and enterprise integrations. It is still not procurement-ready (see "still gapped" below), but it is materially closer.

## Detection depth (Wave 1)

The single-region pHash+DOM scorer was easy to fool. v0.2 adds four detectors that compose with it:

**Multi-region inspection.** `src/inspection/multi_region.py` renders one URL in parallel from N countries via region-pinned proxies, then compares pairwise. Geo-targeted phishing kits only serve their payload to the victim's country and serve benign holding pages elsewhere — exactly the divergence multi-region inspection surfaces. The pipeline runs it on flagged URLs *and* on URLs whose host hints at cloaking (`geo-` substring), so cloaking-only signals reach verdict even when single-region score was below threshold. When cloaking is detected the verdict layer overrides a `benign` LLM verdict to `suspicious / high / watch` because cloaking infrastructure isn't innocent.

**Attack-family classifier.** `src/scoring/family.py` classifies the rendered DOM into one of `m365 / banking / crypto / payment / support / generic` using keyword signature regexes. A family with confidence ≥ 0.6 triggers a per-family scoring-weight profile — crypto kits weight DOM signatures heaviest (the seed-phrase field is the most reliable signal), M365 kits weight visual layout, support-scam pages favour layout + phone number patterns. Family is persisted on the verdict so analysts can batch-triage by kit type.

**Kit fingerprinter.** `src/scoring/template_fingerprint.py` matches DOM + asset URLs + form actions + hidden input names + CSS classes against 6 known phishing kits (16Shop, EvilProxy, Caffeine, Tycoon-2FA, GreatHorn-clone, ModlishkaProxy) plus a known-bad JS bundle hash table. A kit fingerprint match is *strong* evidence — the brand whose login is being cloned might be irrelevant: it matches the kit, not the impersonated brand. Top match gets persisted as `verdict.kit_match` and prepended to the evidence summary.

**Logo embedding scorer.** `src/scoring/logo_embedding.py` replaces the global-histogram logo scorer with either CLIP embeddings (when `transformers + torch` are installed) or a 4×2 spatial-histogram fallback. The spatial fallback alone improves exact-match score from ~0.49 to ~0.89 and stays meaningfully distinguishable on re-coloured logos. CLIP is lazy-loaded so the prototype stays installable from `requirements.txt`.

All four detectors are visible on the alert detail page (signal cards), the dashboard queue (mini-chips per row), the dashboard KPIs (cloaking counter + family/kit breakdown chips), and the PDF evidence pack (Detection signals table).

## Discovery breadth (Wave 2)

v0.1 had three discovery sources (SERP organic, certificate transparency, newly-registered-domains delta). v0.2 adds four more:

| Source | Why it matters |
| --- | --- |
| `paid_ads.py` | Operators outrank legitimate sites by buying ads on brand keywords. Many primary brand-protection vendors only watch organic SERP. |
| `mobile_app_store.py` | Fake Play Store / App Store / APK sideload listings impersonating the brand. Mobile is half of credential-harvest traffic now. |
| `github_leak.py` | Kit source repos, credential dumps, and customised kit forks targeting the brand appear on public GitHub before they're deployed. |
| `telegram_kit.py` | Phishing-as-a-service operators advertise kits on Telegram channels and paste sites *before* the kit goes live — earliest possible signal. |

All four implement the existing `DiscoverySource` protocol so they slot into `run_for_brand()` unchanged. In MOCK_MODE they each emit a small set of plausible fixtures; live-mode hooks are stubbed but not implemented (Bright Data SERP+Unlocker would be the obvious live path for paid ads, app stores, and Telegram, while GitHub needs Web Scraper API + Web Unlocker for rate-limit handling). The full sweep now goes 3→7 sources and 37→107 suspect URLs per brand-pass.

## Platform foundations (Wave 3)

These were entirely missing in v0.1 — every brand was effectively the same tenant, every API call was anonymous, every Bright Data dollar was charged to the same bucket.

**Multi-tenancy.** `src/common/tenants.py` defines `Tenant` + `ApiKey` models. A `tenant_id` column was added to `brands` and `alerts` tables (FK-less to keep the prototype simple). `BrandRepo.list_all(tenant_id=...)` and `AlertRepo.list_for_brand(tenant_id=...)` filter by tenant; the API endpoints enforce isolation so a key issued to tenant A can't see tenant B's brands or alerts.

**API keys with scopes.** `src/storage/repositories_v2.ApiKeyRepo` issues keys with `secrets.token_urlsafe(32)` plaintext secrets that are hashed (SHA-256) at rest and compared with `secrets.compare_digest`. Six scope constants (`alerts:read`, `alerts:triage`, `brands:read`, `brands:write`, `discovery:run`, `admin:*`) gate each route. `src/api/auth.py` provides a `Depends(require_auth("alerts:triage"))` dependency that parses the `Authorization: ApiKey <id>:<secret>` header, authenticates with constant-time secret comparison, enforces scopes, and returns an `AuthCtx(api_key, tenant, actor)` to the route. Strict-auth mode is gated by `REQUIRE_AUTH=true`; when off, anonymous calls fall through unchanged for backward compatibility with the demo.

**Cost attribution.** `CostEventRepo` records every Bright Data API call against a `(tenant_id, brand_id, kind, usd_amount)` row. `total_for_tenant_today()` gives daily spend; `breakdown_for_tenant()` gives per-API-kind decomposition. `GET /api/admin/tenants/{id}/costs` returns daily total, configured cap, and a `cap_reached` flag.

**Audit log.** `AuditLogRepo` writes append-only records of every state-changing operation — tenant creation, key issuance, key revocation, brand creation, alert triage, discovery runs. Each row captures actor, action, target, before/after JSON, request IP, and user agent. Surfaced via `/audit` UI page with filter inputs (tenant, actor, action) and via `GET /api/admin/audit-log`.

**Active learning loop.** `FeedbackEventRepo` captures analyst triage outcomes — `true_positive` from `confirmed`, `false_positive` from `dismissed` — snapshotted with the signal context (family, kit, cloaking, composite score) at decision time. `precision_by_signal("attack_family", "banking")` returns tp/fp counts and precision. The loop is now closed: `src/scoring/active_learning.py` reads accumulated feedback and produces a `TuningReport` with per-signal precision, a threshold recommendation (midpoint between confirmed-alert and dismissed-alert mean scores, clamped to [0.4, 0.9]), and capped (±0.05) weight nudges. It's exposed at `GET /api/admin/tuning`. Recommendations are *advisory* — guardrails refuse output below `min_samples` (default 20), cap nudges, and clamp the threshold, so the system can't silently drift. Auto-apply on a schedule remains a deliberate operator opt-in, not a default.

**Admin router.** `src/api/admin_router.py` mounts at `/api/admin/*` with full tenant CRUD, API key issuance + revocation, cost view, and audit log query. All require the `admin:*` scope. All log to the audit table.

## Enterprise integrations (Wave 4)

v0.1 had Slack + Splunk HEC webhooks. v0.2 adds the four enterprise targets that real customers ask for:

| Integration | File | Auth | Format |
| --- | --- | --- | --- |
| ServiceNow ITSM | `delivery/servicenow.py` | Basic | Incident with severity-mapped impact/urgency + custom field |
| Microsoft Sentinel | `delivery/sentinel.py` | SharedKey HMAC-SHA256 | Log Analytics Data Collector API custom log |
| PagerDuty | `delivery/pagerduty.py` | Routing key | Events API v2 trigger/resolve with dedup_key=alert_id |
| STIX/TAXII | `delivery/taxii.py` | Basic | STIX 2.1 indicator+malware+relationship bundle |

All four share `delivery/integration_base.py` which provides post-with-retry, severity mapping per vendor schema, and HMAC signing for outbound webhooks. Each integration returns `None` when not configured so the pipeline never fails because the customer hasn't connected a target. In mock mode the dispatcher logs which integrations *would* fire without making the network call.

`src/delivery/webhooks.py.dispatch_alert()` calls all configured destinations in parallel-ish fashion and returns a `{destination: status}` map. The webhook payload now includes the new structured signals (`attack_family`, `kit_match`, `cloaking_detected`, etc) so receivers can filter or route on them.

## Workflow depth (Wave 5)

**Takedown automation** (`delivery/takedown/`) was already built in v0.1. v0.2 verified it routes correctly based on `inspection.registrar` and that draft takedown notices include the new signal context.

**Diff detection / time-bomb activations.** `src/inspection/diff_detector.py` re-inspects previously-benign URLs and emits `DiffSignal` rows when a URL has flipped from a holding page to a phishing payload (the "time-bomb" pattern). Single-shot scanners miss this entirely; we now have the foundation to catch it. Scheduling the re-inspection job (every 6-12 hours) is documented but not yet baked into the demo runner.

**Audit log UI** at `/audit` with filter inputs by tenant, actor, and action. Each entry shows timestamp, actor, action, target, tenant, and source IP.

## Test coverage

v0.1 shipped with 24 tests. v0.2 adds 20 more covering:

- Family classifier (3 tests across all 5+1 families)
- Kit fingerprinter (3 tests including a clean-HTML negative)
- Multi-region cloaking detection (2 tests: cloaked + non-cloaked URLs)
- Tenant + API key scope satisfaction
- API key issue/auth/revoke roundtrip (in an isolated tmp DB)
- STIX 2.1 bundle structure (verifies identity + indicator + malware + relationship objects)
- All 4 new discovery sources yielding fixtures
- Active-learning tuner (3 tests: insufficient-data hold, threshold separation, clamping guardrail)
- Alert notes append-only roundtrip
- Prometheus metrics exposition rendering
- Diff-detector time-bomb flip detection

`pytest -q` → `47 passed`.

## Wave 5 follow-ups (post-initial-v0.2)

Three items originally listed as "not reached" were subsequently built:

**Analyst notes thread.** A new append-only `alert_notes` table (distinct from the single overwriteable `alerts.triage_notes`) with `AlertNoteRepo`, `GET`/`POST /api/alerts/{id}/notes` endpoints, and a threaded notes UI on the alert detail page with a JS post handler. Every comment preserves author + timestamp so an investigation has a full who-said-what-when trail. Note additions are audit-logged.

**Diff-detector reachable.** `src/inspection/diff_detector.py` (built earlier but never callable) is now wired to `POST /api/discovery/recheck`. It re-inspects recently-seen URLs and flags time-bomb activations — URLs that rendered benign on first pass but now serve a credential-harvest payload. The mock inspector gained a time-bomb simulation (`timebomb` host hint flips dormant→active on recheck #1+). Fixing the test for this surfaced and fixed a real `DetachedInstanceError` bug: the detector was reading ORM rows out of a closed session.

**Prometheus `/metrics`.** `src/api/metrics.py` exposes gauge metrics in Prometheus text exposition format (`text/plain; version=0.0.4`) without a heavy client dependency — alerts by severity/status, cloaking count, verdicts by family/kit, suspects by source, Bright Data spend by kind, feedback by outcome, tenant + active-key counts. Gated by `PROMETHEUS_ENABLED`. OpenTelemetry tracing remains unimplemented.

## Still gapped

Honestly: most of the procurement checklist from `08-enterprise-readiness.md` is unchanged. v0.2 closed the *technical* gaps (multi-tenancy, RBAC, audit, cost) — but the *organisational* gaps still apply:

- **SOC 2 Type II / ISO 27001** — no change. Still 9-12 months of process work.
- **SSO / SCIM** — not implemented. API keys are the only auth.
- **Data residency** — not implemented. Single-region SQLite.
- **Customer-managed keys** — not implemented. Evidence is encrypted at filesystem level only.
- **Vendor-questionnaire pack** — still needs writing.
- **24/7 paging** — single-developer hackathon project, so no.

Realistic positioning is unchanged from the competitive analysis: this is an OEM-track or design-partner-track product, not a direct-enterprise-procurement one. v0.2 makes that pitch credible by being something a partner could integrate against, where v0.1 was clearly demo-only.

## What did **not** get added

For honesty: things on the v0.2 wish-list that remain unbuilt:

- Live-mode implementations for the four new discovery sources (only fixture data; live SERP-ads, App Store, GitHub, Telegram fetches are stubbed — they need real Bright Data credentials, not appropriate to fake)
- OpenTelemetry distributed tracing (Prometheus metrics now exist; OTel does not)
- Customer-facing webhook signature verification documentation
- Auto-applying active-learning recommendations on a schedule (the report is generated and exposed at `GET /api/admin/tuning`; applying it is still a manual operator decision by design)
