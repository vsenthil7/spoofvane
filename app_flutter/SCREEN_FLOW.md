# SpoofVane — Flutter Console Screen Flow & UI Structure

**Document ID:** `SPOOFVANE-FLUTTER-SCREENFLOW`
**App:** `app_flutter/` (Flutter web SOC console)
**Derived from:** the canonical 21-page console spec — `docs/USER_GUIDE.md` §3,
`console/src/lib/pages.ts` (the React/MeDo/Perplexity convergence registry).
**Note:** this is a *structure derivation*, not a port. None of the MeDo or
Perplexity (React/TS) source is imported; only the screen flow, role model, and
information architecture are mirrored, re-expressed idiomatically in Flutter.

---

## 1. Information architecture

The console is a single authenticated shell (nav rail + top bar + content area)
hosting a set of role-gated pages. One registry (`lib/pages.dart`, the Flutter
analogue of `pages.ts`) is the single source of truth that drives the nav rail,
the router, and role visibility — exactly as the React registry does, so the two
tracks stay structurally aligned.

```
SpoofVaneApp
└── (auth) ──► LoginScreen (P01)            unauthenticated entrypoint
└── (authed) ─► Console shell
                ├── NavRail        (rail entries = pages where nav==true AND role allows)
                ├── TopBar         (search · LIVE/SEED pill · tenant · current role)
                └── ContentArea    ──► selected page's screen
                                       └── deep pages (BrandDetail P04,
                                           AlertDetail P06) pushed over content
```

## 2. Role model (segregation of duties)

Six roles, least → most privileged. A page is visible iff the current role's
rank ≥ the page's `minRole` rank.

| Rank | Role | Adds capability |
|------|------|-----------------|
| 0 | viewer   | read dashboards + settings |
| 1 | auditor  | + audit log, compliance evidence |
| 2 | reviewer | + approve/deny HITL actions (must differ from analyst) |
| 3 | analyst  | + triage, takedowns, discovery |
| 4 | admin    | + users, agents, cost, demo health |
| 5 | owner    | + tenants, billing |

SoD rule (enforced server-side, surfaced in UI): the analyst who raises an alert
cannot be the reviewer who approves its takedown.

## 3. The 21 pages (P01–P21)

| ID | Route | Title | minRole | In rail | Flutter screen | Status |
|----|-------|-------|---------|---------|----------------|--------|
| P01 | /login | Sign in | viewer | no | `LoginScreen` | 🟢 built (demo SSO + role picker) |
| P02 | / | Dashboard | viewer | yes | `DashboardScreen` | 🟢 built |
| P03 | /brands | Brands | analyst | yes | `BrandsScreen` | 🟢 built |
| P04 | /brands/:id | Brand detail | analyst | no | `BrandDetailScreen` | ⬜ planned |
| P05 | /triage | Triage queue | analyst | yes | `TriageScreen` | 🟢 built |
| P06 | /alerts/:id | Alert detail (10 tabs) | analyst | no | `AlertDetailScreen` | 🟢 built (10 tabs) |
| P07 | /clusters | Clusters | analyst | yes | `ClustersScreen` | 🟢 built (LIVE) |
| P08 | /deepfakes | Deepfakes | analyst | yes | `DeepfakeScreen` | 🟢 built |
| P09 | /exec-protection | Exec protection | analyst | yes | `ExecScreen` | 🟢 built |
| P10 | /takedowns | Takedowns | analyst | yes | `TakedownsScreen` | 🟢 built (multi-channel + override) |
| P11 | /audit | Audit | auditor | yes | `AuditScreen` | 🟢 built |
| P12 | /review | Review queue | reviewer | yes | `ReviewQueueScreen` | 🟢 built (SoD-gated) |
| P13 | /cost | Cost | admin | yes | `CostScreen` | 🟢 built (LIVE) |
| P14 | /compliance | Compliance | auditor | yes | `ComplianceScreen` | 🟢 built (SOC2/ISO/DORA/NIS2) |
| P15 | /admin/agents | Agents | admin | yes | `AdminAgentsScreen` | ⬜ planned |
| P16 | /admin/users | Users | admin | yes | `AdminUsersScreen` | ⬜ planned |
| P17 | /admin/tenants | Tenants | owner | yes | `AdminTenantsScreen` | ⬜ planned |
| P18 | /admin/demo-health | Demo health | admin | yes | `AdminDemoHealthScreen` | ⬜ planned |
| P19 | /settings | Settings | viewer | yes | `SettingsScreen` | ⬜ planned |
| P20 | * | Not found | viewer | no | `NotFoundScreen` | ⬜ planned |
| P21 | /403 | Forbidden | viewer | no | `ForbiddenScreen` | ⬜ planned |

The Flutter app currently ships 8 of the 21 screens (the analyst day-to-day
core). This document is the build map for the remaining 13; each lands modularly
with its own widget tests, keeping coverage ≥ 98%.

## 4. The Alert detail (P06) tab structure

P06 is the product's heart — one suspect, ten evidence tabs. Flutter structure:
a `TabBar`/`TabBarView` inside `AlertDetailScreen`, one widget per tab so each is
independently testable.

1. Summary — verdict, score, brand, first seen
2. Evidence — screenshot, DOM, captured assets
3. Multi-region — per-country render (cloaking)
4. Verdict trace — model ensemble (Claude + GPT + Gemini) + dissent
5. MITRE — ATT&CK techniques + D3FEND
6. Kit — matched phishing kit + how
7. Cluster — linked domains
8. Deepfake — face/lip-sync/voiceprint/C2PA (when media present)
9. Takedown — draft packet + submission status
10. Audit — hash-chained trail for this alert

## 5. Navigation flows (primary journeys)

- **Analyst triage:** Dashboard → click KPI/queue → Triage (P05) → row →
  Alert detail (P06) → Verdict trace tab → Takedown tab → request → back to queue.
- **Reviewer approval (SoD):** Review queue (P12) → pending action → approve/deny
  (blocked if the reviewer raised it).
- **Brand onboarding:** Brands (P03) → Brand Wizard → new brand → Brand detail (P04).
- **Admin:** Agents/Users/Tenants/Demo health under /admin/*, role-gated to
  admin/owner.

## 6. Data source honesty (LIVE/SEED)

Every screen reads through `ApiClient` (`lib/api.dart`). When the FastAPI backend
is reachable and returns data the top-bar pill shows **LIVE**; on any failure or
empty payload the screen falls back to bundled seed data and the pill shows
**SEED**. Pages currently confirmed LIVE against the backend: Dashboard, Triage,
Alert detail, Clusters, Cost (see `docs/TRACEABILITY_MASTER.md` §6d).

## 7. Module layout (where things live)

```
app_flutter/lib/
  app.dart            shell (NavRail + TopBar + content), reads pages.dart
  pages.dart          the 21-page registry (id, route, title, minRole, nav, icon)
  roles.dart          Role enum + rank + canSee(page) gate
  theme.dart          SvColors, buildSvTheme
  models.dart         Verdict/Brand/Alert/Cluster/CostRow/AuditRow
  api.dart            ApiClient interface + HttpApiClient + Api.instance
  seed.dart           offline seed data
  widgets/            panel, verdict_pill, stat_card, nav_rail, source_pill, …
  screens/            one file per screen (P01–P21)
test/                 widget + unit tests (mirror lib/)
integration_test/     E2E flows (page objects + flows)
```
