# Product Requirements Document (PRD)

Built by Claude (Opus 4.8) in Claude Code · 29 May 2026, 08:45 BST · SpoofVane v0.5.0

## Personas
- **SOC analyst** — triages alerts, requests takedowns.
- **Reviewer** — approves HITL actions (must differ from the analyst).
- **Brand admin** — onboards brands, sets thresholds, watches cost.
- **Auditor** — reads the hash-chained audit + compliance evidence.

## Capabilities (mapped to module IDs)
- Discovery (A1–A10): SERP, cert-transparency, DNS permutations, registrar/WHOIS
  feed, phishing feeds, social, shortener chains, ads, app stores, crawl seeds.
- Inspection (B1–B8): Scraping-Browser render, cloaking diff, DOM extract, TLS,
  HAR, pHash, WHOIS/ASN, ad-creative capture.
- Scoring (C1–C10): calibrated composite, URL risk, DOM/pHash/logo similarity,
  13-kit fingerprint, family classifier, clustering, voiceprint, deepfake score.
- Verdict (D1–D8): Claude/GPT/Gemini ensemble, SLM cheap-path, dissent-aware
  merge, multimodal, MITRE enrichment, cache + active learning.
- Agents (E1–E10): takedown, victim-id, cred-poison, synth-pages, cluster,
  learning, kill-switch, governance, audit, SLM-triage.
- Delivery (F1–F8): registrar/hosting takedown, 5 SIEM/SOAR sinks, TAXII/STIX,
  own MCP server, Bright Data MCP client.
- Platform (G1–G12): identity, RBAC, audit, HITL, notifications, reports,
  rate-limit, idempotency, cost, chain-of-custody, BYOK, data residency.
- AI surfaces (H1–H10): copilot, NL audit search, brand wizard, deepfake UI,
  exec surface, family reranker, narrator, kit explainer, takedown drafter, TTP.

## UX
21-page SOC console (P01–P21) on a canonical design-token system; analyst-centric
triage → evidence → verdict → takedown flow with full audit.
