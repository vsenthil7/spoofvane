# Security Overview

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST · SpoofVane v0.5.0

- **Identity**: OIDC + SAML + local fallback, TOTP MFA, signed revocable sessions.
- **Authorization**: 6 roles with segregation of duties (analyst ≠ reviewer).
- **Audit**: SHA-256 hash-chained audit log; tamper detection verified in tests.
- **Agent governance**: lawful-basis + two-person + jurisdiction gates for
  offensive/sensitive agents (§V8-5); global/per-tenant kill-switch.
- **Secrets**: BYOK envelope encryption (AWS KMS / Azure KV / GCP KMS adapters).
- **Abuse cases**: see `docs/SECURITY_ABUSE_CASES.md`.
- **Supply chain**: CycloneDX SBOM; SLSA-L3 attestation is CI-gated (BLOCKED-ENV here).
