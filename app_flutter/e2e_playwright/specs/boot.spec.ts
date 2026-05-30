// Smoke E2E: the Flutter app boots in a real browser and the dashboard paints.
import { test, expect } from "@playwright/test";
import { ConsoleShell } from "../pages/console_shell";

test.describe("console boot", () => {
  test("dashboard renders with KPI cards", async ({ page }) => {
    await page.goto("/");
    const shell = new ConsoleShell(page);
    await shell.waitReady();
    await expect(shell.byLabel("Total Alerts")).toBeVisible();
    await expect(shell.byLabel("Takedown Rate")).toBeVisible();
  });
});
