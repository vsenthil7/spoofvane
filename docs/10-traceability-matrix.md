# 10 — Requirements Traceability Matrix (RTM)

**Status:** Living document. Last updated 2026-05-28 (v0.3 identity build).
**Purpose:** Map every requirement to the module that implements it and the
test(s) that verify it, with *honest* coverage and test-type status. This is
the single artefact an auditor or QA lead reads to answer "is this claim
actually tested, and how?"

## How to read this

Each requirement has:

- **ID** — stable identifier (REQ-<area>-<n>).
- **Implementation** — the module(s) that satisfy it.
- **Verified by** — test file(s) / cases. "—" means not yet tested.
- **Test types** — which of {U=unit, I=integration, E=end-to-end/Playwright,
  N=negative} cover it.
- **Status** — ✅ done+tested · 🟡 built, partial tests · 🔴 built, untested ·
  ⬜ not built · 🚫 not code (process/legal/time — tracked in doc 08).

**Coverage honesty rule:** numbers in this document are produced by
`pytest --cov`, not estimated. The current overall line coverage is **66%**
(measured 2026-05-28). We do NOT claim 100%; §6 explains what is deliberately
uncovered and why faking 100% would be a regression in quality.

---

## 1. Identity, authentication & access control (v0.3)

| ID | Requirement | Implementation | Verified by | Types | Status |
|----|-------------|----------------|-------------|-------|--------|
| REQ-AUTH-01 | Users can sign up self-serve (account + owner) | `common/identity.py:signup` | `test_identity.py::test_signup_and_login` | U,I | ✅ |
| REQ-AUTH-02 | Email+password login | `identity.py:authenticate_password` | `test_identity.py::test_signup_and_login` | U,I | ✅ |
| REQ-AUTH-03 | Wrong password rejected | `identity.py` | `test_identity.py::test_bad_password_rejected` | U,N | ✅ |
| REQ-AUTH-04 | Account lockout after 5 failures | `identity.py` (lockout) | `test_identity.py::test_lockout_after_failures` | U,N | ✅ |
| REQ-AUTH-05 | Duplicate email rejected | `identity.py:create_user` | `test_identity.py::test_duplicate_email_rejected` | U,N | ✅ |
| REQ-AUTH-06 | Passwords bcrypt-hashed, ≥8 chars | `common/security.py:hash_password` | `test_identity.py::TestSecurity` | U,N | ✅ |
| REQ-AUTH-07 | Long-password bcrypt 72-byte footgun closed | `security.py:_prehash` | `test_identity.py::test_long_password_no_collision` | U,N | ✅ |
| REQ-AUTH-08 | JWT access + refresh tokens | `security.py:issue_*` | `test_identity.py::test_jwt_roundtrip_and_type_check` | U,N | ✅ |
| REQ-AUTH-09 | Token type confusion prevented | `security.py:decode_token` | `test_identity.py::test_jwt_roundtrip_and_type_check` | U,N | ✅ |
| REQ-AUTH-10 | Signed, revocable web sessions | `identity.py:*_web_session` | `test_identity.py::test_session_lifecycle` | U,I | ✅ |
| REQ-AUTH-11 | Tampered session cookie rejected | `security.py:load_session` | `test_identity.py::test_session_sign_load` | U,N | ✅ |
| REQ-MFA-01 | TOTP MFA enrolment | `identity.py:begin/confirm_mfa` | `test_identity.py::test_mfa_flow` | U,I | ✅ |
| REQ-MFA-02 | Login demands MFA when enabled | `identity.py:authenticate_password` | `test_identity.py::test_mfa_flow` | U,I | ✅ |
| REQ-MFA-03 | One-time recovery codes | `security.py`, `identity.py` | `test_identity.py::test_recovery_code_works_once` | U,N | ✅ |
| REQ-SSO-01 | OIDC login + JIT provisioning | `identity.py:upsert_oidc_user`, `auth_router.py` | `test_identity.py::test_oidc_jit_provision` (logic); E2E ⬜ | U,I | 🟡 |
| REQ-SSO-02 | OIDC callback over HTTP | `auth_router.py:oidc_callback` | — (needs mock IdP) | — | 🔴 |
| REQ-RBAC-01 | 6 roles + platform staff | `common/rbac.py` | `test_identity.py::TestRbacMatrix` | U | ✅ |
| REQ-RBAC-02 | Segregation of duties: analyst ≠ approver | `rbac.py` | `test_rbac::test_segregation_of_duties` + live deps test | U | ✅ |
| REQ-RBAC-03 | Admin cannot bill/delete account | `rbac.py` | `test_identity.py::test_admin_cannot_touch_billing` | U | ✅ |
| REQ-RBAC-04 | Viewer is read-only | `rbac.py` | `test_identity.py::test_viewer_is_read_only` | U | ✅ |
| REQ-RBAC-05 | Service identity can never decide | `rbac.py` | `test_identity.py::test_service_role_can_never_decide` | U | ✅ |
| REQ-RBAC-06 | Route-level permission gate (HTTP 403) | `api/deps.py:require` | API integration test (TestAuthApi) | I,N | 🟡 |
| REQ-TIER-01 | 4 tiers Personal→Enterprise | `rbac.py` | `test_identity.py::TestTiers` | U | ✅ |
| REQ-TIER-02 | Feature gating by tier (HTTP 402) | `rbac.py`, `deps.py:require_feature` | API integration test | I,N | 🟡 |
| REQ-TIER-03 | Quota escalation by tier | `rbac.py:limits_for` | `test_identity.py::test_quota_escalates` | U | ✅ |
| REQ-UI-01 | Login page renders | `web/templates/login.html`, `app.py:/login` | E2E (Playwright) | E | 🟡 |
| REQ-UI-02 | MFA step in login UI | `login.html` | E2E (Playwright) | E | 🟡 |
| REQ-UI-03 | Demo-user quick-fill | `login.html`, `demo_users.py` | E2E (Playwright) | E | 🟡 |
| REQ-SEED-01 | Full role×tier demo matrix seeded | `scripts/seed_users.py` | manual run verified; auto-test ⬜ | I | 🟡 |

## 2. Detection pipeline (v0.1–0.2, pre-existing)

| ID | Requirement | Implementation | Verified by | Types | Status |
|----|-------------|----------------|-------------|-------|--------|
| REQ-DET-01 | Discover suspects across 7 surfaces | `discovery/*` | `test_discovery.py`, `test_v02_features.py` | U,I | ✅ |
| REQ-DET-02 | Render + inspect page (browser) | `inspection/browser.py` | `test_pipeline.py` | U,I | 🟡 (72%) |
| REQ-DET-03 | pHash / DOM / logo / favicon scoring | `scoring/*` | `test_scoring.py` | U | ✅ |
| REQ-DET-04 | Composite score w/ renormalisation | `scoring/composite.py` | `test_scoring.py` | U | 🟡 (82%) |
| REQ-DET-05 | Attack-family classification | `scoring/family.py` | `test_v02_features.py::TestFamily` | U | ✅ |
| REQ-DET-06 | Phishing-kit fingerprinting | `scoring/template_fingerprint.py` | `test_v02_features.py::TestKit*` | U | ✅ |
| REQ-DET-07 | Multi-region cloaking detection | `inspection/multi_region.py` | `test_v02_features.py::TestMultiRegion` | U | ✅ |
| REQ-DET-08 | Time-bomb diff detection | `inspection/diff_detector.py` | `test_v02_features.py::test_timebomb` | U | ✅ |
| REQ-DET-09 | AI verdict (Claude vision) | `verdict/claude_verdict.py` | `test_verdict.py` | U | 🟡 (71%) |
| REQ-DET-10 | Logo CLIP embedding | `scoring/logo_embedding.py` | — | — | 🔴 (0%) |
| REQ-DET-11 | Evidence hash-chain ledger | `storage/repositories*`, pipeline | `test_pipeline.py` | U,I | 🟡 |

## 3. Human-in-the-loop, notifications, reports (Phases 3–5 — IN PROGRESS)

| ID | Requirement | Implementation | Verified by | Types | Status |
|----|-------------|----------------|-------------|-------|--------|
| REQ-HITL-01 | AI verdict creates pending review, no auto-action | `common/review.py:enqueue_for_review` | `test_ops.py::TestReview` | U | ✅ |
| REQ-HITL-02 | Reviewer approve/reject/escalate | `review.py:decide`, `ops_router.py` | `test_ops.py::TestReview` | U,I,N | ✅ |
| REQ-HITL-03 | Only approved verdict → takedown submit | `review.py:decide` (takedown_eligible gate) | `test_ops.py::test_approve_makes_takedown_eligible`, `test_reject_blocks_takedown` | U,N | ✅ |
| REQ-HITL-04 | Decision feeds active-learning loop | `review.py:_feed_active_learning` | `test_ops.py::test_decision_writes_audit_and_feedback` | U | ✅ |
| REQ-NOTIF-01 | In-app notification feed | `common/notifications.py:notify/list_for_user` | `test_ops.py::TestNotifications` | U,I | ✅ |
| REQ-NOTIF-02 | Email alerts (SMTP/SES) | `notifications.py:_send_smtp/_maybe_email` | `test_ops.py::test_email_skipped_when_not_configured` (live SMTP = staging) | U | 🟡 |
| REQ-NOTIF-03 | Per-user subscription prefs | `notifications.py:get_pref/set_pref`, `ops_router` | `test_ops.py` + recipients logic | U | ✅ |
| REQ-NOTIF-04 | System-error / SLA-breach alerts | `review.py:sweep_sla_breaches` -> notify | `test_ops.py::test_sla_breach_sweep` | U | ✅ |
| REQ-RPT-01 | Detection summary report | `common/reports.py:generate_detection_summary` | `test_ops.py::TestReports` (pdf/csv/json) | U | ✅ |
| REQ-RPT-02 | Executive / board pack | `reports.py:generate_board_pack` | `test_ops.py::test_board_pack_pdf` | U | ✅ |
| REQ-RPT-03 | Audit export (CSV/JSON) | `reports.py:generate_audit_export`, `ops_router` | `test_ops.py::test_audit_export_csv_includes_chain` | U,I | ✅ |
| REQ-RPT-04 | On-demand generation (scheduled = celery beat, wired) | `ops_router.py:/api/reports/{kind}` | API integration | I | 🟡 |

## 4. Audit & observability (Phase 2 — NEXT)

| ID | Requirement | Implementation | Verified by | Types | Status |
|----|-------------|----------------|-------------|-------|--------|
| REQ-AUD-01 | Every mutating action logged | `api/audit_middleware.py` | end-to-end middleware proof | I | ✅ |
| REQ-AUD-02 | Capture actor/IP/UA/before→after | `common/audit.py:record` | `test_ops.py::TestAuditChain` | U | ✅ |
| REQ-AUD-03 | Tamper-evident hash chain | `audit.py:_compute_hash/verify_chain` | `test_ops.py::test_tamper_is_detected` | U,N | ✅ |
| REQ-AUD-04 | Audit UI w/ filters | `audit_log.html` (exists, basic) | E2E ⬜ | — | 🟡 |
| REQ-AUD-05 | Audit CSV/JSON export | `audit.py:export_*`, `ops_router:/api/audit/export` | `test_ops.py::test_csv_export` + API | U,I | ✅ |
| REQ-OBS-01 | Prometheus metrics | `api/metrics.py` | covered 100% | U | ✅ |
| REQ-OBS-02 | Structured logging | `common/logging.py` | implicit | U | ✅ |

## 5. Coverage, takedown & integrations (Phase 6)

| ID | Requirement | Implementation | Verified by | Types | Status |
|----|-------------|----------------|-------------|-------|--------|
| REQ-TKD-01 | Draft DMCA/abuse takedown | `delivery/takedown/*` | — | — | 🔴 (0%) |
| REQ-TKD-02 | Submit to registrar/host APIs (gated) | `takedown/{cloudflare,godaddy,namecheap}` | — | — | 🔴 (0%) |
| REQ-INT-01 | ServiceNow / Sentinel / PagerDuty | `delivery/*` | partial | — | 🟡 |
| REQ-INT-02 | STIX/TAXII export | `delivery/taxii.py` | `test_v02_features.py::test_stix` | U | 🟡 (78%) |
| REQ-INT-03 | HMAC-signed webhooks | `delivery/webhooks.py` | `test_webhooks.py` | U | 🟡 (37%) |
| REQ-INT-04 | MCP server | `delivery/mcp_server.py` | — | — | 🔴 (0%) |

## 6. Deliberately uncovered — and why (anti-fakery register)

100% line coverage is **not** the goal; verified behaviour is. The following
are knowingly uncovered, with rationale, so no one mistakes the gap for an
oversight:

| Area | Why not covered by unit tests | How it IS / will be assured |
|------|------------------------------|-----------------------------|
| `delivery/takedown/*` registrar APIs | Calling real GoDaddy/Cloudflare/Namecheap APIs needs live creds + would issue real takedowns | Contract tests against recorded fixtures (planned); never live in CI |
| `delivery/mcp_server.py` | Long-running stdio server process | E2E harness that spawns + speaks MCP (planned) |
| `scoring/logo_embedding.py` | Loads a CLIP model (heavyweight) | Tested behind a feature flag with a stub embedder; real model is integration-only |
| `claude_verdict.py` live branch | Real Anthropic call | Mock-mode path IS tested; live path exercised in staging only |
| `pdf_evidence.py` rendering internals | ReportLab layout | Output-shape assertion test (planned) + visual smoke in E2E |
| `__main__` blocks / glue | Entry points, not logic | Exercised by E2E + manual run |

## 7. Test-type coverage scorecard (the four dimensions asked for)

| Dimension | Where it stands (2026-05-28, measured) | Target |
|-----------|----------------------------------------|--------|
| **Unit** | strong on identity/rbac/security/scoring/audit/review/reports | maintain ≥90% on business logic |
| **Integration (API/HTTP)** | extensive — auth, ops (review/notif/reports/audit), admin, product API, all via TestClient across roles | maintain |
| **End-to-end (Playwright)** | suite WRITTEN (`tests/e2e/`, 6 cases: login, bad-login, demo-fill, MFA reveal, logout). **Skips in this sandbox — Chromium binary download is blocked by the network allowlist.** Runs in CI/local via `tests/e2e/run_e2e.sh`. NOT yet witnessed green. | execute in CI; add dashboard + RBAC-redirect cases |
| **Negative** | comprehensive: forged/tampered/misused JWTs, tampered cookies, injection-shaped inputs, privilege escalation, tier gating, cross-tenant isolation, bad-input 422, bad-state 400, wrong-scope 403 | maintain |
| **Line coverage** | **81% overall** (was 66%). Owned v0.3 modules: rbac 100%, identity_models 100%, ops_router 96%, reports 97%, audit 96%, identity 95%, security 96%, review 90%, admin_router 93%, legacy auth 98%, deps 85%, app.py 68% | 85%+ on testable modules |

**Test counts:** 207 passing + 3 skipped (E2E, browser-gated). Four real bugs
were found and fixed *by* these tests: (a) naive/aware datetime comparison
that broke account lockout on SQLite; (b) access token omitted `tier`, which
broke feature-gating over the API; (c) Viewer role wrongly had review-queue
access; (d) Pydantic protected-namespace warning on VerdictResult.

## 8. Change log of this document

- 2026-05-28 — created during v0.3 identity build; baselined coverage at 66%;
  enumerated Phases 2–6 requirements as ⬜ to make the remaining scope explicit.
