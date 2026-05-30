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
    // glasspane / flutter-view appears once the engine is up.
    await this.page.waitForSelector("flt-glass-pane, flutter-view", {
      timeout: 30_000,
    });
    // Flutter web does not populate the semantics tree (the <flt-semantics>
    // nodes Playwright queries by aria-label) until accessibility is enabled.
    // It exposes an "Enable accessibility" placeholder button for exactly this;
    // activating it builds the semantic DOM. This is the supported way to drive
    // a CanvasKit Flutter app from the DOM.
    await this.enableAccessibility();
    // Dashboard title is the first-paint anchor.
    await expect(this.byLabel("Security Dashboard")).toBeVisible({
      timeout: 30_000,
    });
  }

  /** Click the Flutter "Enable accessibility" placeholder so the semantics DOM
   *  is populated. Safe to call repeatedly. */
  async enableAccessibility(): Promise<void> {
    // Dispatch a real click on the placeholder element from inside the page —
    // Flutter listens for a click/pointer event on it to turn semantics on.
    await this.page.evaluate(() => {
      const el = document.querySelector(
        'flt-semantics-placeholder, [aria-label="Enable accessibility"]'
      ) as HTMLElement | null;
      if (el) {
        ['pointerdown', 'pointerup', 'click'].forEach((type) =>
          el.dispatchEvent(
            new (type.startsWith('pointer') ? PointerEvent : MouseEvent)(type, {
              bubbles: true,
              cancelable: true,
            })
          )
        );
      }
    });
    await this.page.waitForSelector("flt-semantics", { timeout: 15_000 });
  }

  /** Any node whose accessible name contains [text]. */
  byLabel(text: string): Locator {
    return this.page
      .locator(`[aria-label*="${text}"], flt-semantics:has-text("${text}")`)
      .first();
  }

  /** A semantic node that contains [text] — used to assert the content area
   *  changed after navigation (matches body text painted by the active screen). */
  contentHasText(text: string): Locator {
    return this.page.locator(`flt-semantics:has-text("${text}")`).first();
  }

  /** Click a nav-rail destination by its label. The rail tiles are exposed as
   *  role=button semantic nodes whose label is the destination name. */
  async navigateTo(navLabel: string): Promise<void> {
    const button = this.page
      .locator(`flt-semantics[role="button"]:has-text("${navLabel}")`)
      .first();
    await button.click({ force: true });
    // Let the content area rebuild.
    await this.page.waitForTimeout(500);
  }

  pill(which: "LIVE" | "SEED"): Locator {
    return this.byLabel(which);
  }
}
