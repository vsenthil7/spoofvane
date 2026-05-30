// E2E: navigate the rail across surfaces in a real browser.
import { test, expect } from "@playwright/test";
import { ConsoleShell } from "../pages/console_shell";

test.describe("rail navigation", () => {
  test("navigates dashboard -> triage -> cost -> audit", async ({ page }) => {
    await page.goto("/");
    const shell = new ConsoleShell(page);
    await shell.waitReady();

    await shell.navigateTo("Triage Queue");
    await expect(shell.byLabel("Triage Queue")).toBeVisible();

    await shell.navigateTo("Cost Attribution");
    await expect(shell.byLabel("Cost Attribution")).toBeVisible();

    await shell.navigateTo("Audit Log");
    await expect(shell.byLabel("Audit Log")).toBeVisible();
  });
});
