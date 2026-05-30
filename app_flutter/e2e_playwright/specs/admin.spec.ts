// E2E: sign in as owner (the most privileged role) and verify an admin-only
// surface renders. The login screen has a "Demo role" dropdown; we pick owner
// so the rail exposes the admin/owner pages (Agents, Users, Tenants, Demo
// health) that an analyst would not see.
import { test, expect } from "@playwright/test";
import { ConsoleShell } from "../pages/console_shell";

test.describe("admin surfaces (owner role)", () => {
  test("owner can reach the agent kill-switch", async ({ page }) => {
    await page.goto("/");
    const shell = new ConsoleShell(page);

    // Boot + enable semantics (without the default analyst login).
    await page.waitForSelector("flt-glass-pane, flutter-view", { timeout: 30_000 });
    await shell.enableAccessibility();

    // Pick the owner role from the dropdown, then sign in.
    await shell.clickByText("Analyst"); // opens the role dropdown (current value)
    await shell.clickByText("Owner"); // select owner
    await shell.clickByText("Sign in");
    await page.waitForTimeout(800);

    // Dashboard first.
    await expect(shell.byLabel("Security Dashboard")).toBeVisible({ timeout: 30_000 });

    // Navigate to the Agents admin screen and confirm the kill-switch renders.
    await shell.navigateTo("Agents");
    await expect(shell.contentHasText("kill-switch")).toBeVisible({ timeout: 15_000 });
  });
});
