# 08 — Enterprise Readiness Gap Analysis

**Status:** Self-audit, May 2026. Scored against an enterprise security buyer's procurement checklist.

This complements `07-competitive-analysis.md`. That doc covered "what features do incumbents have that we don't." This doc covers the operational, security, and platform requirements that procurement teams use to disqualify vendors *before* a feature comparison ever happens.

The scoring is deliberately conservative. Any "✓" claim here has to survive a real customer security questionnaire (CAIQ, SIG, vendor risk assessment).

---

## 1. Overall readiness score: **24 / 100**

| Category | Weight | Score | Weighted |
|---|---|---|---|
| Core product capability | 20% | 6/10 | 12 |
| Security & compliance | 20% | 1/10 | 2 |
| Multi-tenancy & data isolation | 15% | 1/10 | 1.5 |
| Identity & access management | 10% | 1/10 | 1 |
| Reliability & operations | 10% | 2/10 | 2 |
| Integrations & ecosystem | 10% | 2/10 | 2 |
| Audit & observability | 5% | 3/10 | 1.5 |
| Documentation & support | 5% | 4/10 | 2 |
| Commercial / contractual | 5% | 0/10 | 0 |
| **Total** | **100%** | | **24** |

Anything under 70 doesn't pass a serious enterprise procurement gate. We are exactly where you'd expect a 4-day hackathon prototype to be — strong on the core technical demo, near zero on everything procurement actually checks.

This document lays out exactly what each gap is and what it costs to close.

---

## 2. Detailed gap inventory

Each row shows: capability · current state · what enterprise buyers expect · estimated effort to close.

### 2.1 Security & compliance

| Item | Current | Required for enterprise | Effort |
|---|---|---|---|
| SOC 2 Type II | None | Required by ~85% of Fortune 1000 procurement | 9–12 months elapsed; ~$60–120K external audit cost |
| ISO 27001 | None | Required by most EU, APAC enterprises | 6–9 months elapsed; concurrent with SOC 2 |
| GDPR data processing addendum (DPA) | None | Required for any EU customer | 2–4 weeks legal + ongoing |
| HIPAA BAA | N/a (no PHI today) | Required if any healthcare customer | When relevant; ~4 weeks |
| Penetration test (third-party) | None | Annual at minimum | $15–40K per test |
| Encryption at rest | SQLite file unencrypted | AES-256 with KMS / customer-managed keys | 1–2 weeks engineering |
| Encryption in transit | TLS via uvicorn (dev) | Mutual TLS option; HSTS; modern cipher suites enforced | 1 week |
| Secrets management | `.env` file | HashiCorp Vault / AWS Secrets Manager / GCP Secret Manager | 2–3 weeks |
| Customer-managed keys (CMK) | None | Required by financial-services buyers | 4–8 weeks |
| Data residency (EU / US / APAC) | Single instance | Region-pinned deployments; data never crosses | 6–12 weeks |
| PII handling policy | None | Documented; data classification scheme | 2–4 weeks policy + tooling |
| Right-to-be-forgotten workflow | None | Hard-delete with cascade across blobs | 2 weeks |
| Vulnerability disclosure programme | None | Required for security buyers | 1 week to set up |

### 2.2 Multi-tenancy & data isolation

| Item | Current | Required | Effort |
|---|---|---|---|
| Per-tenant DB schema | Single shared SQLite | Row-level security OR schema-per-tenant OR cluster-per-tenant | 4–8 weeks |
| Per-tenant evidence segregation | Shared `data/evidence/` | Tenant-scoped buckets with IAM enforcement | 3–4 weeks |
| Per-tenant rate limits | None | Token bucket per tenant + per-API-key | 2 weeks |
| Cross-tenant data leak prevention | No enforcement | RLS policies, query interceptors, automated tests | 4–6 weeks |
| Tenant onboarding workflow | Manual SQL | Self-serve signup + admin invite + tenant provisioning API | 6–8 weeks |
| Tenant offboarding / data export | None | Export to S3, full delete with proof | 3 weeks |

### 2.3 Identity & access management

| Item | Current | Required | Effort |
|---|---|---|---|
| SSO (SAML 2.0) | None | Required by virtually all enterprise buyers | 3–4 weeks (use a library like SAML SP) |
| SSO (OIDC) | None | Increasingly required | 2 weeks |
| SCIM provisioning | None | Required for >500-seat customers | 4–6 weeks |
| MFA enforcement | None | Required | 2 weeks |
| Role-based access control | Two implicit roles (analyst, admin) | Granular permissions across resources | 6–8 weeks |
| API keys with scopes | None | Per-key scopes (read-only, brand-specific, etc.) | 2–3 weeks |
| Session management | FastAPI default | Configurable timeouts, concurrent session limits | 1–2 weeks |

### 2.4 Reliability & operations

| Item | Current | Required | Effort |
|---|---|---|---|
| Uptime SLA | None | 99.9% baseline; 99.95% for enterprise tier | Architecture rework |
| HA deployment | Single-node | Multi-AZ active/active or active/standby | 4–6 weeks |
| Disaster recovery | None | RTO < 4h, RPO < 1h documented and tested | 4–8 weeks |
| Backup + restore | Manual SQLite copy | Automated, encrypted, tested restore | 2–3 weeks |
| Capacity planning | None | Per-tenant inspection budget; queue depth alerts | 2 weeks |
| Status page | None | Required (statuspage.io, instatus, or self-hosted) | 1 week |
| 24×7 on-call | None | PagerDuty rota; runbook for every alert | Hiring + 4 weeks process |
| Incident-response playbook | Three placeholder playbooks in `docs/04-runbook.md` | Real playbooks; rehearsed; post-incident reviews | Ongoing |

### 2.5 Integrations & ecosystem

| Item | Current | Required for enterprise SIEM/SOAR integration |
|---|---|---|
| Slack webhook | Stub | First-class app, OAuth install, block-kit messages, slash commands |
| Splunk HEC | Stub | First-class Splunk TA + CIM-compliant field mapping |
| Microsoft Sentinel | None | Sentinel solution + analytic rules + KQL functions |
| Google Chronicle | None | Parser + UDM mapping |
| Palo Alto Cortex XSOAR | None | Pack with playbooks |
| ServiceNow ITSM | None | Bidirectional sync with incident tickets |
| Jira Service Management | None | Bidirectional sync |
| PagerDuty | None | Webhook integration with event routing |
| Tines / Torq / n8n | None | Verified actions in marketplace |
| MISP threat intel | None | MISP event publishing |
| STIX/TAXII feed | None | Required by many SOCs |
| Generic webhook with signed HMAC | Partial | Industry-standard HMAC-SHA256 signing on every payload |
| OpenAPI spec | Auto-generated via FastAPI | Hand-curated, with examples, error codes, idempotency keys |
| SDKs | None | Python, TypeScript, Go (most common asks) |

### 2.6 Audit & observability

| Item | Current | Required |
|---|---|---|
| Inspection-evidence tamper proof | ✓ (hash chain) | ✓ (already strongest area) |
| Admin audit log | None | Every state change logged with actor, timestamp, before/after |
| Triage audit log | Partial (alert.triaged_by, triaged_at) | Full event log; immutable |
| Export of audit log to customer | None | API + UI download in CEF / JSON |
| Structured logging | ✓ (structlog) | ✓ |
| Metrics (Prometheus / OTel) | None | Required for ops |
| Distributed tracing | None | OTel traces across discovery → inspection → verdict |
| Cost-per-tenant attribution | None | Required for sustainable unit economics |

### 2.7 Commercial / contractual

| Item | Current | Required |
|---|---|---|
| MSA template | None | Standard MSA covering IP, liability, indemnification, termination |
| Order form template | None | |
| DPA template | None | |
| Sub-processor list | Not published | Required by GDPR Article 28 |
| Cyber-liability insurance | None | Typically $5M minimum to win RFPs |
| E&O insurance | None | Typically $2M minimum |
| Support SLAs | None | P1: 1h response 24×7; P2: 4h business hours; etc. |

---

## 3. The shortest credible path to procurement-ready

You don't need to close every gap above to start landing customers. The minimum credible bar for an enterprise security buyer is:

**Tier 1 (must have to even start the conversation, ~4 months):**
- SSO (SAML + OIDC)
- Encryption at rest + secrets management
- Multi-tenancy with row-level security
- Per-tenant rate limits + cost attribution
- Admin audit log
- Status page + uptime SLA target
- Cyber-liability insurance ($5M)
- SOC 2 Type I audit started

**Tier 2 (must have to close most enterprise deals, ~6 more months):**
- SOC 2 Type II achieved
- Splunk + Sentinel + ServiceNow integrations (the three most-asked SIEM/ITSM in 2026)
- 8×5 support with documented SLAs
- Pen-test report shareable under NDA
- DPA + sub-processor list

**Tier 3 (must have for Fortune 500, ~12 more months):**
- ISO 27001
- Customer-managed keys
- EU + US data residency
- 24×7 on-call
- HIPAA BAA (if pursuing healthcare)
- Federal-grade controls (FedRAMP Moderate if pursuing US gov)

Total: ~22 elapsed months from prototype to Fortune-500-ready, assuming 5 engineers + 1 compliance lead + 1 customer-success hire. Faster only by buying compliance-as-a-service (Vanta, Drata, Secureframe).

---

## 4. The OEM shortcut

There is a faster path: don't sell direct to enterprises. Sell the **detection engine** to one of the existing brand-protection vendors as an OEM "hard-to-reach pages" feed.

The partner brings:
- SOC 2 / ISO 27001 already
- Their existing multi-tenancy
- Their existing customer base
- Their SOC and takedown relationships
- Their RFP-passing reputation

We bring:
- The Bright-Data-powered detection wedge
- An evidence-pack format their existing pipeline can consume
- A simple per-inspection or per-tenant licence model

This shrinks the "enterprise-grade" requirement from a 22-month roadmap to:
- A reliable production deployment of the engine
- A clean API surface (we have it)
- A pen-test + basic compliance hygiene
- A commercial structure (licence + per-call pricing)

OEM is the realistic 12-month path to seven-figure ARR. Direct enterprise sales is the realistic 36-month path. Both can run in parallel, but if forced to choose, the OEM path closes the credibility gap faster.

---

## 5. What this means for the current submission

Nothing in this document changes what should be built or demonstrated *for the hackathon*. The hackathon prototype is correctly scoped — it demonstrates the wedge (geo-pinned residential rendering + DOM/screenshot fingerprinting + evidence ledger) at a depth that's hard to do in 4 days and impossible to fake. Everything in section 2 of this doc is what we'd build *afterwards*.

What this document **does** change is the pitch. When a judge asks "is this enterprise-ready?", the honest answer earns more points than the bluff:

> *"Not yet. The detection wedge is real and we've shown it working end-to-end. Production-ready is 12 months of compliance and platform work, OR ~6 months as an OEM feed inside an existing brand-protection vendor — and we've mapped both paths in the docs."*

That answer signals technical depth, commercial maturity, and self-awareness. Bluffing the answer signals the opposite.

---

*End of enterprise readiness analysis.*
