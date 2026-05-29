# Requirements Traceability Matrix (RTM) — convergence addendum

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST · SpoofVane v0.5.0

This addendum maps the review's module IDs to implementation + tests. The
original per-feature RTM remains at `docs/10-traceability-matrix.md`; the full
module/page/BD-product matrix is in `docs/TRACEABILITY_MASTER.md`.

| Requirement area | Module IDs | Test evidence |
|------------------|-----------|---------------|
| Discovery breadth | A1–A10 | test_discovery_s2.py + existing discovery tests |
| Inspection depth | B1–B8 | test_inspection_s3.py |
| Scoring + calibration | C1–C10 | test_scoring_s4.py, test_deepfake_s5.py |
| Verdict ensemble | D1–D8 | test_verdict_s6.py |
| Governed agents | E1–E10 | test_agents_s7.py (15 cases) |
| Delivery sinks | F1–F8 | test_delivery_s8.py |
| Platform controls | G1–G12 | test_platform_s9.py |
| AI surfaces | H1–H10 | test_ai_surfaces_s10.py |
| 21-page console | P01–P21 | test_console_parity_s13.py + tsc clean |
| Sponsor 7/7 | BD clients | test_brightdata_clients.py + tests/depth |
| Supply chain | SBOM/SLSA | test_supply_chain_s14.py |
