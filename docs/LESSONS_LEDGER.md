# Lessons Ledger (review §V8-6)

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST

Durable record of lessons applied during the convergence build.

1. **Stubs masquerading as features are the top procurement risk.** Every module
   now carries a differential-probe test before it can be called "real."
2. **Sponsor integrations must be one package, not scattered config.** All BD
   access funnels through `src/integrations/brightdata/`.
3. **Offensive capability needs lawful-basis + two-person + jurisdiction gates,
   not just a consent boolean** (§V8-5) — enforced in `GovernanceEngine`.
4. **Reproducibility beats live demos for review.** Replay mode lets any
   reviewer run every code path with no credentials.
5. **Honest status documents win trust.** 🔒 BLOCKED-ENV is used instead of
   silently dropping infeasible requirements.
