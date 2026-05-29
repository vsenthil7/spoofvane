# Anti-Pattern Ledger (review §V9-7)

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST

This ledger records anti-patterns the review identified in the pre-convergence
codebase and the control that prevents each from recurring. A reviewer diffs
this file each cycle; a regression against any row is a P0.

| ID | Anti-pattern observed | Why it's harmful | Control now in force |
|----|----------------------|------------------|----------------------|
| AP-1 | A status doc claimed 18 modules "fully coded" when they were 6–12-line stubs | Documentation overstating code is a procurement-loss risk | "Fully coded" is banned unless the module passes the §0.1 differential probe in `tests/depth/`. The `TRACEABILITY_MASTER` uses 🟢/🟡/⬜/🔒 honest states. |
| AP-2 | A 6-line `inspection/browser.py` returned a stub page; a sponsor product reduced to a name | Sponsor product reduced to a name; no real value | Every Bright Data product has a real client in `src/integrations/brightdata/clients.py` with a live path + input-dependent replay; `{"mock": True}` constant returns are forbidden (depth probe fails them). |
| AP-3 | Claiming 100/100 coverage / 7-of-7 live BD without proof | False assurance to buyers | `STATUS.md` claims only what tests/artefacts prove; blocked items are 🔒 BLOCKED-ENV with the reason. |
| AP-4 | Self-referential cross-track import ("import from your own track") | Tracks never actually converge | §V8-1 corrected mapping documented in `TRACEABILITY_MASTER`. |

## Differential-probe enforcement

`tests/depth/test_differential.py` feeds ≥3 distinct inputs to each implemented
module and asserts ≥3 distinct outputs. A constant-returning stub fails. Current
status: **14 module probes green** (7 BD clients + C1/C2/C9/C10 + D2 + H5/H7).
