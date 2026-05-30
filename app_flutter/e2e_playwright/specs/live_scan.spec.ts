// E2E: the Live Scan screen (P26, DEMO-1). The Playwright suite runs against a
// static Flutter-web build with NO backend, so a real *live* scan cannot run
// here (it needs the FastAPI server + real BD/LLM keys — that path is proven by
// tests/test_scan_live.py against the real services). What we verify in-browser
// is what CAN be verified statically:
//   1. The scan screen is reachable from the rail and renders its inputs.
//   2. The live/demo toggle is present and switchable.
//   3. In DEMO mode (which needs no backend) running a scan produces a result
//      card with the multi-LLM ensemble votes — proving the UI wiring works.
// We deliberately do NOT assert a live result here; doing so would either fake
// it or flake on network. The live path has its own real-service test.
import { test, expect } from "@playwright/test";
import { ConsoleShell } from "../pages/console_shell";

test.describe("live scan screen (P26)", () => {
  test("reachable from the rail; demo mode runs a multi-LLM ensemble", async ({
    page,
  }) => {
    await page.goto("/");
    const shell = new ConsoleShell(page);
    await shell.waitReady();

    // Navigate to the Live Scan screen.
    await shell.navigateTo("Live Scan");
    // The screen title + the input affordances render.
    await expect(shell.contentHasText("Live Scan")).toBeVisible({
      timeout: 15_000,
    });
    await expect(shell.contentHasText("Suspect URL")).toBeVisible();

    // Switch to Demo mode (no backend needed) and run a scan.
    await shell.clickByText("Demo");
    await shell.clickByText("Scan");
    await page.waitForTimeout(1200);

    // The result card shows the multi-LLM ensemble: model names + DEMO tag.
    await expect(shell.contentHasText("Claude")).toBeVisible({ timeout: 15_000 });
    await expect(shell.contentHasText("GPT")).toBeVisible();
    await expect(shell.contentHasText("Gemini")).toBeVisible();
    await expect(shell.contentHasText("DEMO")).toBeVisible();
  });
});
