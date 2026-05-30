// E2E: navigate the rail across analyst-visible surfaces in a real browser.
// The default console role is analyst, so the rail shows Dashboard, Brands,
// Triage Queue, Campaign Clusters, Deepfake Feed, Exec Protection, Takedowns,
// Audit Log, Review queue, Compliance, Settings (admin/owner pages are gated
// out — asserted in the role-gating widget tests).
import { test, expect } from "@playwright/test";
import { ConsoleShell } from "../pages/console_shell";

test.describe("rail navigation", () => {
  test("navigates dashboard -> triage -> clusters -> audit", async ({ page }) => {
    await page.goto("/");
    const shell = new ConsoleShell(page);
    await shell.waitReady();

    // Land on the dashboard.
    await expect(shell.byLabel("Security Dashboard")).toBeVisible();

    await shell.navigateTo("Triage Queue");
    await expect(shell.contentHasText("alert")).toBeVisible();

    await shell.navigateTo("Campaign Clusters");
    await expect(shell.contentHasText("Campaign")).toBeVisible();

    await shell.navigateTo("Takedowns");
    await expect(shell.contentHasText("channels")).toBeVisible();

    await shell.navigateTo("Audit Log");
    await expect(shell.contentHasText("Audit")).toBeVisible();
  });
});
