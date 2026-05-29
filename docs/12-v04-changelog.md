# 12 — v0.4 Changelog: Social Channel + Agentic AI Triage Copilot

**Date:** 2026-05-28
**Theme:** Close the single largest *detection* gap the competitive analysis
named (social-media impersonation), and add the agentic "max AI usage" layer
that turns the analyst console into a conversational SOC assistant.

Like v0.3, this release is **purely additive**. Nothing in v0.1–v0.3
(detection engine, 7 discovery surfaces, family/kit/cloaking, evidence chain,
integrations, IAM/RBAC/MFA/SSO, audit, HITL review, notifications, reports,
gated takedown) is removed or weakened.

---

## 1. Social-media impersonation discovery (NEW)

`docs/07-competitive-analysis.md` §3 marks SpoofVane `✗` on **social-media
impersonation** while ZeroFox, BrandShield, Bolster, Red Points, Cyble and
Constella all ship it — the biggest single-channel gap in the matrix, and the
most common reason a buyer says "this is a feed, not a platform."

`src/discovery/social_media.py` adds an eighth discovery surface that finds
brand impersonation across X, Instagram, Facebook, TikTok, LinkedIn, YouTube,
Telegram and Threads. It classifies each hit into one of three impersonation
**surfaces**:

* `handle_squat` — squatted handles (`@acmebank-support`).
* `fake_support_account` — profiles that reply to real customers then DM them
  to a credential-harvesting page.
* `impersonation_page` — cloned company pages / groups with a malicious link.

**Why this fits the Bright Data wedge.** Social platforms heavily rate-limit
and anti-bot their own APIs, but their public profile/page URLs are reachable
through the SERP API + Web Unlocker + residential-proxy stack the product
already uses. Live mode queries each platform with a `site:` filter; the
profile's *out-link* (the page victims are funnelled to) becomes the inspection
target, so the new channel reuses the **entire** existing inspection → scoring →
verdict → evidence path rather than duplicating it.

Registered in the default sweep (`run_once.DEFAULT_SOURCES["social_media"]`) and
fully covered by mock fixtures so it demos offline.

## 2. Agentic AI Triage Copilot (NEW)

`src/verdict/copilot.py` adds the "max AI usage" layer. v0.1–v0.3 used a single
Claude *call* per page. The Copilot is a multi-turn **agent**: an analyst asks a
natural-language question and Claude autonomously decides which queries to run
against the alert/evidence store, then answers with citations back to alert ids.

* **Tool surface is the MCP contract.** The agent's tools are the exact read
  handlers already exposed by `src/delivery/mcp_server.py` (`query_alerts`,
  `get_evidence`, `draft_takedown`). One place to audit; the agent can do
  nothing a human MCP user couldn't.
* **Read-only by default.** The only state-mutating MCP tool (`mark_triaged`)
  is withheld unless `allow_actions=True`, which the API gates behind the
  `alerts:triage` permission. Even then the agent can only move triage state —
  it can **never** approve or submit a takedown. The v0.3 human-in-the-loop
  gate in `src/common/review.py` is preserved exactly.
* **Bounded.** The loop terminates after `max_iterations` tool rounds.
* **Offline-safe.** With `MOCK_MODE` or no API key, a deterministic planner
  answers the common intents by calling the same tools directly — identical in
  spirit to the `VerdictEngine` fallback, so the demo and tests run with no
  network.

Exposed at `POST /api/copilot/ask` (RBAC-gated, audited via the existing
middleware).

## 3. Competitive matrix movement

`docs/07-competitive-analysis.md` §3 social-media row updated:
`✗` → `~` for **SpoofVane (today)** (web-funnel detection across 8 platforms;
not yet full in-platform social listening) and `~` → `✓` on the 12-month
roadmap column.

## 4. Testing & quality

* **+16 tests** (207 → 223 passing, 3 browser-gated E2E still skipped):
  * `tests/test_social_discovery.py` — 7 tests: registration, fixture yield,
    platform/surface metadata, funnel-target selection, classifier, handle
    extraction.
  * `tests/test_copilot.py` — 5 tests: alert listing, evidence explanation,
    takedown drafting without sending, the read-only-by-default guarantee,
    graceful no-result handling.
  * `tests/test_ops_http.py::TestCopilotHttp` — 4 tests: viewer read-only ask,
    viewer denied actions-mode (403), analyst allowed actions-mode,
    unauthenticated denied (401).
* No regressions; full suite green in `MOCK_MODE`.

## 5. Honest status

* The social source is a **web-funnel** detector across social platforms — it
  finds the impersonating profile and inspects the page it points victims to.
  It is **not yet** full in-platform social listening (post/comment streams,
  takedown via each platform's trusted-flagger programme); that remains a
  roadmap item, hence `~` not `✓` in the matrix.
* The Copilot's offline planner covers the common triage intents; the full
  reasoning breadth is only available in live mode with an Anthropic key. Both
  paths are tested.
* Nothing here changes the procurement-readiness picture in
  `docs/08-enterprise-readiness.md` §1 — those gaps remain non-code (SOC 2/ISO,
  pentest, takedown partners, 24×7 staffing).

---

*End of v0.4 changelog.*
