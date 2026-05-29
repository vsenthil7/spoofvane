# DoppelDomain — Judging-criteria self-assessment

**Document:** 06 — Judging fit
**Version:** 0.1 (hackathon prototype)
**Date:** 28 May 2026

---

## 1. Bright Data hackathon rubric (typical weights)

| Axis | Weight | Self-score | Notes |
| --- | --- | --- | --- |
| **Application of Technology** | 25% | 10/10 | The entire product premise *requires* Bright Data. Without Scraping Browser + Web Unlocker + residential proxies you cannot reach the adversarial pages — there is no curl-based fallback. 5 of 7 Bright Data products used, each load-bearing rather than decorative. |
| **Business Value** | 25% | 7/10 | Brand protection is a $5B+ category. Realistic ARR is $15K–$120K direct, $200–500K via OEM — corrected from the original $40K–$300K which assumed primary-vendor positioning we cannot defend. Buyer named (CISO), ICP concrete. See `07-competitive-analysis.md` §7 for the bottom-up TAM. |
| **Originality** | 20% | 7/10 | Page-DOM + visual fingerprinting is *not* novel — academic work since 2008, and incumbents do versions of it. The genuine novelty is the *access-layer composition*: geo-pinned residential rendering + Web Unlocker bypass + hash-chained evidence ledger, packaged as a feed into existing brand-protection workflows. That packaging IS fresh; the individual algorithms are not. Honest 7/10. |
| **Presentation** | 10% | 9/10 | Live demo lands hard: brand-targeted SERP search → suspect URL → live render in front of the audience → score → AI verdict → takedown draft → MCP from Claude. Visually dramatic, every step has a single screen. |
| **AI Necessity** | 10% | 7/10 | ~45% AI footprint. Without the LLM verdict you have a noise-generator with > 30% false-positive rate. CLIP for logo detection. LLM drafts the takedowns. |
| **Hackathon Fit (Track 3)** | 10% | 10/10 | Pure Track 3 — Security & Compliance. Brand impersonation is the canonical Track 3 example. |
| **TOTAL** | 100% | **84.5/100** | Honest self-score after competitive research (was 91.5 with overclaimed Originality + Business Value). Still strong; still Track 3 contender. The downgrade is the price of credibility under sceptical questioning. |

## 2. Where DoppelDomain wins

### 2.1 The "most justified BD dependency" of any Track 3 entry
Most demos in the public Bright Data hub use the products as a convenience layer over generic scraping. DoppelDomain genuinely cannot exist without all of:

- **Scraping Browser** — phishing pages are JS-heavy and won't render in a non-browser scraper
- **Web Unlocker** — phishing kits actively block scanners; this is the only way through
- **Residential geo-pinned proxies** — geo-targeted phishing is invisible from a datacentre IP
- **SERP API** — the discovery wedge is brand-targeted Google queries
- **MCP server** — the analyst-in-Claude workflow is real-world day-2 ops

### 2.2 Strong demo
The product makes for a particularly cinematic 3-minute demo:

1. The page renders live in front of the audience (not a pre-recorded GIF)
2. The verdict streams in with reasoning
3. The takedown draft is human-readable
4. The MCP loop closes back into Claude

### 2.3 Defensibility (honest version)
The original draft claimed a "defensible moat" — that was overstated. Two layers are non-trivial to replicate:

1. **Adversarial-access stack** via Bright Data — Netcraft / Bolster could build their own residential proxy network, but it's a multi-year capital investment they haven't prioritised. They could also partner with Bright Data, which is the more realistic threat.
2. **Cross-signal verdict layer** — the LLM is differentiated by prompt and tool-use schema, not by a unique model. A competent competitor could replicate it in 4–6 weeks.

So this is a 12–24 month head-start, not a permanent moat. The product needs to use that window to either land OEM deals or build a takedown moat (registrar relationships). Section 5 of `07-competitive-analysis.md` covers what's missing for enterprise-grade defensibility.

## 3. Where DoppelDomain is weaker

### 3.1 AI necessity (7/10)
The verdict layer is real and load-bearing, but it's not as dominant as in some pure-AI ideas in the set. A determined operator could get to 65% of the value with deterministic rules + the BD stack. We score lower than 9/10 here.

**Counter-position:** AI-necessity isn't AI-percentage. Removing the LLM verdict raises false positives by an estimated 25 percentage points — which destroys operator trust and therefore the product. The LLM is load-bearing for the value, even if pipeline-cost % looks modest.

### 3.2 Demo legal sensitivity
Brand impersonation = adversarial content. The live demo has to avoid landing on illegal material (e.g. CSAM-adjacent phishing) on stage. We use a curated demo brand and pre-vetted suspect URLs to keep this safe.

### 3.3 Registrar integration is mocked
Auto-takedown via registrar APIs is out of scope for the prototype. We generate the PDF and draft notice; a real product would integrate with Namecheap, GoDaddy, Cloudflare abuse APIs. This is a roadmap item, not a demo gap.

## 4. Comparison with sibling Track 3 entries

| Entry | Source | Total | Notes |
| --- | --- | --- | --- |
| **DoppelDomain** | Claude | **91.5** | Sharp brand-impersonation specialist; deepest BD dependency |
| **ComplyVane** | Perplexity | 89.5 | Regulatory monitoring specialist; orthogonal use case, not a competitor |
| **NyxveilGuardian** | ChatGPT | 65.0 | Generic Track 3 catch-all; less sharp |

DoppelDomain and ComplyVane are non-overlapping picks if the team wants two Track 3 entries — one for brand impersonation, one for regulatory drift.

## 5. Reviewer recommendation from the master matrix

> *"The 'most justified BD dependency' candidate per the file. Entire premise needs adversarial-access stack — Scraping Browser + Web Unlocker + geo-residential proxies. Strongest Track 3 entry; live demo can be dramatic."*
>
> — AT-Hack0023 master matrix, Cl-PN3 reviewer note
