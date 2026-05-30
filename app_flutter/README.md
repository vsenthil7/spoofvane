# SpoofVane Flutter Console (`app_flutter/`)

The runnable SOC console for SpoofVane — a Flutter **web** app that mirrors the
21 canonical screens + the commercial surface (API keys, Pricing, Usage,
Billing, Registration, Onboarding), wired to the FastAPI backend with an honest
**LIVE / SEED** data-source pill.

There is **no hosted public URL** — the app runs locally. Below is exactly how to
view it and how it works.

---

## How to view it (3 ways)

### 1. Quickest — serve the pre-built web bundle
A compiled build already exists at `build/web/` (≈2.3 MB `main.dart.js`).
Serve it with any static server and open the page:

```bash
cd app_flutter/build/web
python -m http.server 8080
# then open http://localhost:8080
```

This shows the UI in **SEED mode** (no backend behind a static server), so every
screen renders with realistic offline data and the pill reads **SEED**.

### 2. Live — run against the real backend
In one terminal start the API (seed it first so screens have LIVE data):

```bash
# repo root
.venv\Scripts\python -m scripts.seed_demo          # seed brand+alerts+tenant+users+reviews+keys
.venv\Scripts\python -m uvicorn src.api.app:app --reload   # serves http://localhost:8000
```

In another terminal run the Flutter app pointed at it:

```bash
cd app_flutter
flutter run -d chrome --dart-define=API_BASE=http://localhost:8000
```

Now the pill reads **LIVE** and the 14 wired screens read real backend data
(pricing, compliance, tenants, usage, demo-health, review, api-keys, agents,
users, takedowns, billing, deepfakes, clusters, cost).

### 3. Rebuild the web bundle yourself
```bash
cd app_flutter
flutter build web                      # output in build/web/
# or with semantics for E2E:
flutter build web --dart-define=E2E=true
```

---

## How it works (architecture)

- **Entry:** `lib/main.dart` → `LoginScreen` (demo SSO + a 6-role picker so you
  can see each role's gated menu) → `Console(role:)` shell (nav rail + top bar +
  content).
- **Single page registry:** `lib/pages.dart` (`kPages`, P01–P25) drives the nav
  rail, the router, and role visibility — one source of truth. `lib/roles.dart`
  is the 6-role rank gate (viewer→owner) with segregation-of-duties.
- **Data layer:** `lib/api.dart` — an abstract `ApiClient` (DI seam) with
  `HttpApiClient` that calls `http://localhost:8000/api/...` first and falls back
  to the offline `lib/seed.dart` data, flipping the `DataSource` pill LIVE↔SEED.
  So the UI is always honest about whether it's showing real or canned data.
- **Models:** `lib/models.dart` — every model has both camelCase and snake_case
  `fromJson` so live JSON and seed both deserialize.
- **Screens:** `lib/screens/` — 21 canonical + commercial screens.
- **Widgets:** `lib/widgets/` — Panel, StatCard, VerdictPill, SourcePill,
  NavRail, ScreenTitle (shared design system from `lib/theme.dart`, palette
  sampled from the MeDo reference screenshots in `design_refs/`).

## Tests (see `TESTING.md` for full commands)
- **Widget/unit:** `flutter test` → 108 passed, 98.5% line coverage (FakeApi DI).
- **Integration:** `flutter drive` page-object flows (browser; needs ChromeDriver).
- **Playwright E2E:** `cd e2e_playwright && npm test` → 3 specs in real Chromium
  (boot, role-gated navigation, admin kill-switch).

## Source on GitHub
`https://github.com/vsenthil7/spoofvane` → `app_flutter/`. The compiled
`build/web` is gitignored (build artifact), so to view you build/serve locally
per the steps above.
