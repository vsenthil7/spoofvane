# Reproducible Build & Replay (review §V9-5)

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST

```bash
export SPOOFVANE_BD_MODE=replay          # default — no Bright Data account needed
python -m pytest --ignore=tests/e2e -q   # 326 passing, 2 skipped
python -m pytest tests/depth -q          # 14 differential probes green
```

Every Bright Data client runs the SAME code in replay as in live; only the
transport differs (recorded/seeded fixture vs network). This means a reviewer on
a clean host exercises the real code paths without credentials. Set
`SPOOFVANE_BD_MODE=live` + `BRIGHTDATA_*` env vars for the sponsor-live lane.

**🔒 BLOCKED-ENV:** byte-identical SLSA-L3 provenance and a signed container
image require a CI builder + registry not present in this sandbox; the SBOM is
generable locally (S14).
