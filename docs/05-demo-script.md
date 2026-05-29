# DoppelDomain — 3-minute demo script

**Document:** 05 — Demo script
**Version:** 0.1 (hackathon prototype)
**Date:** 28 May 2026

---

## 0. Pre-flight (before going on stage)

- [ ] `MOCK_MODE=false` in `.env`, real Bright Data + Anthropic keys set
- [ ] One fixture brand "DemoBank" already onboarded
- [ ] Two fixture phishing pages running locally (a `legitimate-looking` clone and an unrelated-domain clone), served at `https://demo-phish-1.local` and `https://demo-phish-2.local`
- [ ] Tabs ready: dashboard at `/`, an empty Claude session in a second window
- [ ] Backup screen-recording in case live demo fails

## 1. The hook (15 seconds)

> *"The number one entry vector for credential theft in 2026 is not a typosquat. It's an unrelated-looking domain hosting a perfect clone of your login page, served only to visitors in the victim country, behind Cloudflare. Existing brand-protection tools cannot see it — because they can't even reach the page. We built **DoppelDomain** to fix exactly that."*

## 2. The problem in two slides (30 seconds)

**Slide 1.** Side-by-side: real DemoBank login page (left) vs phishing clone at `account-update-portal.xyz` (right). Identical. Point at the URL bar: *"The domain has no DemoBank string in it. Every existing tool misses this."*

**Slide 2.** A 403 from a generic crawler hitting the phishing page. *"And when a scanner does try to reach it — this is what it gets. The phishing kit blocks every security scanner specifically."*

## 3. The demo (90 seconds)

### Beat 1 — Discovery (15s)
Tab to the dashboard. Click **"Run discovery"** for DemoBank. The Discovery panel ticks up live as SERP results + cert-stream hits flow in. *"412 suspect URLs surfaced in the last minute — across our three feeds."*

### Beat 2 — Inspection (30s)
Click into the top URL in the queue. Show the inspection panel populating live:
- Screenshot rendering in front of us
- DOM hash appearing
- Network log filling
*"Behind the scenes, that's the Bright Data Scraping Browser running real Chrome from a residential IP in our target country — bypassing the Cloudflare challenge the phishing kit put up. No other stack does this end-to-end."*

### Beat 3 — Scoring (15s)
The four scores light up: pHash 0.96, DOM 0.81, logo 0.93, favicon-match ✅. Composite 0.91. *"All four signals agree."*

### Beat 4 — Verdict (20s)
The Claude verdict streams in:
> *"This page renders the DemoBank logo identically to the canonical login. The login form posts to a non-DemoBank domain. The domain was registered 2 days ago via Namecheap on a low-reputation ASN. **High-confidence phishing.**"*

The takedown draft appears in the panel below — addressed to Namecheap's abuse team.

### Beat 5 — MCP from Claude (10s)
Tab to the Claude window. Type *"Use DoppelDomain MCP. Show me all critical open alerts for DemoBank from the last hour."* Claude calls the MCP server, returns the list, offers to draft takedowns. Click accept on one. *"Analysts can run the whole loop from inside Claude."*

## 4. Why Bright Data (30 seconds)

> *"This entire product premise depends on Bright Data. Scraping Browser is what gives us real Chrome on a residential IP. Web Unlocker is what gets us past the anti-scanner wall the phishing kit puts up — specifically to block tools like ours. Residential geo-targeted proxies are what let us see geo-pinned phishing payloads. SERP API is the discovery wedge. MCP server brings the whole thing into the analyst's existing Claude workflow."*
>
> *"5 of 7 Bright Data products — with the most justified technical dependency of any Track 3 entry."*

## 5. Close (15 seconds)

> *"We're not pitching a Netcraft replacement. We're pitching a complementary feed that reaches phishing pages incumbents can't — geo-blocked, Cloudflare-fronted, anti-bot-protected. Realistic ARR is $30–80K as an add-on into existing brand-protection workflows, or 6-figure OEM licences into the incumbents themselves. We've shown discovery → render → score → verdict → evidence pack, end-to-end, in three minutes. That's DoppelDomain."*

## 6. Q&A preparation

| Likely question | Honest answer |
| --- | --- |
| How is this different from Netcraft? | Netcraft is mature and has 20 years of takedown relationships. Our wedge is reaching geo-pinned, anti-bot-protected pages their crawl footprint struggles with. We're a feed *into* a Netcraft pipeline, not a replacement. |
| What about Memcyco's in-session detection? | Different problem. Memcyco protects users on the brand's own site in real time. We tell you what attacker infrastructure exists across the open web. Buy both — they're complementary. |
| Is page-DOM similarity novel? | No — academic work since 2008, and incumbents do versions of it. Our wedge is the *access layer* (residential geo-pinning + Web Unlocker), not the similarity algorithm. |
| Won't phishing kits detect Bright Data IPs? | Residential rotation. The whole point of residential proxies is that the IPs are indistinguishable from real customers. We also avoid known scanner fingerprints (browser canvas, viewport patterns). |
| False-positive rate? | Two-tier: composite-score gate, then LLM verdict. < 5% target after verdict. Conservative thresholds at onboarding. |
| What if the LLM is wrong? | The verdict is structured with evidence and confidence. Analysts triage. The system surfaces, it doesn't auto-take-down. Every takedown draft is marked "for legal review", never auto-sent. |
| Is this enterprise-ready? | Not yet. We've documented the gap honestly in `08-enterprise-readiness.md`. Realistic path is 12 months as an OEM feed, 22+ months as a direct-sales product. |
| Mobile-app store impersonation? | Not in the prototype. Same engine, different discovery feed — Q2 roadmap item. |
| Why not URLScan / PhishTank? | Latency, coverage, crowd-sourced. We're proactive and per-brand, with structured per-page evidence and a tamper-evident ledger. |
| What's a realistic ARR? | $15–35K mid-market add-on; $50–120K enterprise multi-brand; $200–500K OEM licence. The original draft quoted $40–300K — that was wrong for this positioning, and the corrected bottom-up TAM is in `07-competitive-analysis.md` §7. |
