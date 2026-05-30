import { defineConfig, devices } from "@playwright/test";

// Playwright E2E for the Flutter web build. The Flutter app is built with
// --dart-define=E2E=true (semantics tree enabled) so the CanvasKit canvas
// exposes a DOM Playwright can query by aria-label / role. The webServer builds
// the app once and serves build/web on :5599 for the duration of the run.
//
// Run:  npm install && npx playwright install chromium && npx playwright test
export default defineConfig({
  testDir: "./specs",
  fullyParallel: true,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5599",
    viewport: { width: 1280, height: 800 },
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    // Build the E2E bundle (semantics on) then serve it statically.
    command:
      'cmd /c "C:\\flutter\\bin\\flutter.bat build web --dart-define=E2E=true --no-tree-shake-icons && npx http-server build/web -p 5599 -s"',
    url: "http://127.0.0.1:5599",
    timeout: 180_000,
    reuseExistingServer: true,
  },
});
