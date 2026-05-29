# Business Requirements Document (BRD)

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST · SpoofVane v0.5.0

## Problem
Brands lose revenue and trust to phishing sites, fake mobile apps, social
impersonation, fraudulent ads, and — increasingly — executive deepfakes (voice
and video) used in BEC and market manipulation. Detection is fragmented across
point tools; takedown is manual and slow.

## Business goals
1. Detect brand/executive impersonation across web, app stores, social, ads, and
   media within minutes of going live.
2. Cut mean-time-to-takedown by automating research → draft → submit behind a
   human-in-the-loop gate.
3. Give SOC analysts one console with auditable, court-ready evidence.
4. Operate within a predictable per-tenant cost envelope.

## Success metrics
- Coverage: ≥7 discovery surfaces live per brand.
- Precision: calibrated verdict probability, analyst-overridable, closed-loop.
- Governance: every offensive action carries a lawful basis + two-person rule.
- Cost: per-tenant Bright Data spend stays within tier envelope.

## Out of scope (v0.5)
Live third-party verification lanes, SLSA-L3 signing, and the pixel-parity React
migration are scheduled but environment-blocked in this build (see STATUS.md).
