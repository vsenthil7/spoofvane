// Page objects for the Flutter-web E2E suite. Flutter's semantics tree renders
// into the DOM as <flt-semantics> nodes carrying aria-label / role attributes
// (because we built with --dart-define=E2E=true). These objects locate elements
// by their semantic label — the same labels declared via Semantics() widgets
// and via visible text — so specs stay declarative.
import { Page, Locator, expect } from "@playwright/test";

export class ConsoleShell {
  constructor(private readonly page: Page) {}

  /** Wait for Flutter to boot and paint its semantic DOM. */
  async waitReady(): Promise<void> {
    // glasspane / semantics host appears once the engine is up.
    await this.page.waitForSelector("flt-glass-pane, flutter-view", {
      timeout: 30_000,
    });
    // Dashboard title is the first-paint anchor.
    await expect(this.byLabel("Security Dashboard")).toBeVisible({
      timeout: 30_000,
    });
  }

  /** Any node whose accessible name contains [text]. */
  byLabel(text: string): Locator {
    return this.page
      .locator(`[aria-label*="${text}"], flt-semantics:has-text("${text}")`)
      .first();
  }

  async navigateTo(navLabel: string): Promise<void> {
    await this.byLabel(navLabel).click();
  }

  pill(which: "LIVE" | "SEED"): Locator {
    return this.byLabel(which);
  }
}
