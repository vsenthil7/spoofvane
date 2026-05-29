# SpoofVane — Build Status

**Product:** SpoofVane v0.5.0 (`spoofvane-convergence-v9`)
**Coder:** Claude (Opus 4.8) in Claude Code · **Issued:** 29 May 2026, 08:45 BST
**Tracks:** AT-Hack0023-P01-SpoofVane review stack (Perplexity v9 ⊇ Claude v8 ⊇ ChatGPT v7 ⊇ Claude v6)

> Honest status per the anti-pattern rules. No metric is claimed unless a test or
> runtime artefact proves it. See `docs/TRACEABILITY_MASTER.md` for the full ledger.

## Scoreboard (true as of this build)

| Dimension | Target | Now | Notes |
|-----------|--------|-----|-------|
| Backend module IDs (real) | 76/76 | **76 real** | all have input-dependent impls + tests |
| Differential depth probe | all | **14 module probes green** | `tests/depth/` (BD+scoring+deepfake+verdict+AI) |
| Bright Data products (code path) | 7/7 | **7/7 built** | live verification BLOCKED-ENV (no creds) |
| Bright Data live 24h-green | 7/7 | 🔒 BLOCKED-ENV | needs BD account + outbound |
| UI pages | 21/21 | **~10 real/partial (Jinja)** | React canonical console = S13 |
| Unit/integration tests | 100% | **326 passing, 2 skip** | +103 over v0.4 baseline (223) |
| E2E Playwright | 21 pages | 6 specs (need live server) | server fixture = follow-up |
| Supply chain (SBOM/SLSA) | L3 | 🔒 BLOCKED-ENV | no CI/registry in sandbox |
| Rebrand DoppelDomain→SpoofVane | 100% | **✅ 0 residual** | tests green across rename |

## Run it (credential-free, reproducible — review §V9-5)

```bash
export SPOOFVANE_BD_MODE=replay        # default; no Bright Data account needed
python -m pytest --ignore=tests/e2e -q # 326 passing
python -m pytest tests/depth -q        # 14 differential probes green
```

Set `SPOOFVANE_BD_MODE=live` with `BRIGHTDATA_*` env vars to exercise the real
`brd.superproxy.io` / `api.brightdata.com` paths in the sponsor-live lane.
