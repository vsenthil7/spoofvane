// v06 §A — Sidebar collapse Playwright spec (Gate 1).
//
// Asserts: expanded rail ~232px; clicking the toggle collapses to exactly 64px;
// nav labels become aria-hidden in collapsed mode; pressing "[" flips state.
//
// NOTE: execution needs a running vite dev server + browsers → BLOCKED-ENV in
// the build sandbox. The spec is real and runs in CI. The collapse *logic* is
// additionally proven by the runnable unit test in src/lib/sidebar.test.ts.
import { test, expect } from "@playwright/test";

const BASE = process.env.CONSOLE_BASE ?? "http://127.0.0.1:5173";

test("rail expands to ~232px and collapses to 64px with aria-hidden labels", async ({ page }) => {
  await page.goto(`${BASE}/`);
  const rail = page.getByTestId("sidebar-rail");
  await expect(rail).toBeVisible();

  const expandedW = await rail.evaluate((el) => el.getBoundingClientRect().width);
  expect(Math.round(expandedW)).toBeGreaterThanOrEqual(220);

  await page.getByTestId("sidebar-toggle").click();
  await expect(rail).toHaveAttribute("data-collapsed", "true");
  const collapsedW = await rail.evaluate((el) => el.getBoundingClientRect().width);
  expect(Math.round(collapsedW)).toBe(64);

  // A nav label must be aria-hidden when collapsed.
  const label = page.getByTestId("nav-label-P02");
  await expect(label).toHaveAttribute("aria-hidden", "true");
});

test("[ keyboard shortcut toggles the rail", async ({ page }) => {
  await page.goto(`${BASE}/`);
  const rail = page.getByTestId("sidebar-rail");
  const before = await rail.getAttribute("data-collapsed");
  await page.keyboard.press("[");
  const after = await rail.getAttribute("data-collapsed");
  expect(after).not.toBe(before);
});

test("detail route auto-collapses the rail (route-aware)", async ({ page }) => {
  await page.goto(`${BASE}/triage`);
  const rail = page.getByTestId("sidebar-rail");
  await expect(rail).toHaveAttribute("data-collapsed", "true");
});
