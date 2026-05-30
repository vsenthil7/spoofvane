# SpoofVane Flutter Console — Testing

Three layers, each runnable independently.

## 1. Widget + unit tests (headless, fast — the coverage backbone)
```
flutter test --coverage
```
30 tests, **98.5% line coverage**. Every screen and widget at 100%. Uses
`FakeApi` (no network) for screens and `http` `MockClient` for the real
`HttpApiClient`. Coverage report: `coverage/lcov.info`.

## 2. Integration tests (real app, full user flows)
Modular page-objects (`integration_test/pages/`) + per-flow specs
(`integration_test/flows/`): triage→takedown, full rail navigation, offline
(SEED) mode. Flutter web integration tests run in a real browser via
ChromeDriver:
```
chromedriver --port=4444 &
flutter drive \
  --driver=test_driver/integration_test.dart \
  --target=integration_test/flows/triage_takedown_flow_test.dart \
  -d chrome
```
(`flutter test integration_test` is not supported for web-only projects — use
`flutter drive`.)

## 3. Playwright E2E (real browser, semantics-driven)
The app is built with `--dart-define=E2E=true` so Flutter's semantics tree is
exposed in the DOM and Playwright can query by accessible label. Modular
page-objects (`e2e_playwright/pages/`) + specs (`e2e_playwright/specs/`).
```
cd e2e_playwright
npm install
npx playwright install chromium
npx playwright test            # builds the E2E web bundle + serves + runs
```
The `webServer` block builds `build/web` (semantics on) and serves it on :5599
for the run.

## Notes
- Playwright is the secondary E2E layer for the Flutter (canvas) app; the
  widget+integration layers are the primary coverage. Playwright is also the
  right tool for the React console (`../console/e2e/`, real DOM).
