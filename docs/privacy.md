# Privacy & Data Protection

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST · SpoofVane v0.5.0

- **Data residency**: tenant data pinned to EU/US/APAC/IN; cross-region ops are
  blocked with a `ResidencyViolation` and a non-egress proof record (G12).
- **Lawful basis**: sensitive agents (victim-id, exec-surface) record a named
  GDPR Art.6/9 (or ECCTA, UK) basis per action, surfaced in the audit row.
- **Minimisation**: victim identification correlates session telemetry behind a
  consent/DPIA gate and flags PII-minimised output.
- **Chain-of-custody**: deepfake evidence carries a tamper-evident custody chain
  for legal discovery (G10).
- **DPIA**: `docs/EXEC_PROTECTION_DPIA.md` (exec-protection surface).
