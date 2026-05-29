# Architecture

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST · SpoofVane v0.5.0

```
                 ┌──────────────── SOC Console (21 pages, React/TS) ────────────────┐
                 │  canonical design tokens · role-gated nav · evidence tabs        │
                 └───────────────▲───────────────────────────────▲──────────────────┘
                                 │ REST/JSON                      │
                 ┌───────────────┴───────────────────────────────┴──────────────────┐
                 │                       FastAPI app (src/api)                        │
                 │  auth · RBAC · audit middleware · ops/admin routers · metrics      │
                 └───┬──────────┬──────────┬───────────┬───────────┬──────────┬───────┘
        Discovery A* │ Inspect B*│ Scoring C*│ Verdict D*│ Agents E* │Delivery F*│ AI H*
                 ┌───┴──────────┴──────────┴───────────┴───────────┴──────────┴───┐
                 │            Canonical Bright Data package (7 products)            │
                 │  live / replay / mock dispatch · cost + usage recording          │
                 └──────────────────────────────────────────────────────────────────┘
   Platform G*: identity · audit (hash-chain) · HITL · notifications · reports ·
               rate-limit · idempotency · cost · chain-of-custody · BYOK · residency
```

Single source of truth for Bright Data access; every sponsor call is cost-tracked
and audited. Agent actions pass through a governance gate (blast-radius, lawful
basis, two-person, jurisdiction) before execution and are appended to a
hash-chained agent ledger.
