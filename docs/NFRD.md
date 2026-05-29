# Non-Functional Requirements (NFRD)

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST · SpoofVane v0.5.0

| Attribute | Requirement | Status |
|-----------|-------------|--------|
| Security | OIDC/SAML, MFA, RBAC w/ SoD, hash-chained audit, BYOK | 🟢 |
| Privacy | Data residency (EU/US/APAC/IN), DPIA for sensitive agents | 🟢 |
| Reproducibility | One-command credential-free build (replay mode) | 🟢 |
| Cost | Per-tenant envelope enforcement, SLM-first routing | 🟢 |
| Reliability | Idempotency keys, rate limiting, kill-switch | 🟢 |
| Auditability | Tamper-evident chains (audit, agent, chain-of-custody) | 🟢 |
| Supply chain | CycloneDX SBOM; SLSA-L3 signing | 🟡 SBOM real / signing 🔒 |
| Performance (pixel parity) | ≤5% Playwright diff across tracks | 🔒 BLOCKED-ENV |
