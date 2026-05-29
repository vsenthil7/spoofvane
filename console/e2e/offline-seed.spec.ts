// v06 §C — offline render Playwright spec (Gate 3).
//
// With the backend NOT started, every nav route must still render via the
// seed lane, and the Demo Health pill must read SEED. Run with VITE_DEMO=seed
// (or simply no backend) so api.ts falls back to seed.ts.
//
// NOTE: execution needs a running vite dev server + browsers → BLOCKED-ENV in
// the build sandbox. Spec is real and runs in CI. The seed data integrity is
// additionally proven by the runnable node:test in src/lib/seed.test.ts.
import { test, expect } from "@playwright/test";
import { PAGES } from "../src/lib/pages";

const BASE = process.env.CONSOLE_BASE ?? "http://127.0.0.1:5173";

for (const page of PAGES) {
  if (page.route.includes(":") || page.route === "*" || !page.nav) continue;
  test(`${page.id} ${page.title} renders backend-down`, async ({ page: pw }) => {
    await pw.goto(`${BASE}${page.route}`);
    await expect(pw.locator("body")).toBeVisible();
    // Demo Health pill must indicate the seed fallback engaged.
    const pill = pw.getByTestId("demo-health-pill");
    await expect(pill).toHaveAttribute("data-source", "seed");
  });
}

test("a seeded alert id is visible on the triage queue backend-down", async ({ page }) => {
  await page.goto(`${BASE}/triage`);
  await expect(page.getByText("alert_seed_001")).toBeVisible();
});
