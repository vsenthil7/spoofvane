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
    await this.enableAccessibility();
    // The app opens on the Login screen; click a demo SSO option to enter the
    // console, then the Dashboard is the first-paint anchor.
    await this.demoLogin();
    await expect(this.byLabel("Security Dashboard")).toBeVisible({
      timeout: 30_000,
    });
  }

  /** Click a demo sign-in option (Continue with Google) to enter the console.
   *  Flutter processes real pointer events at coordinates, so we click the
   *  centre of the semantic node's bounding box rather than dispatching a DOM
   *  click (which the canvas ignores). */
  async demoLogin(): Promise<void> {
    const google = this.page
        .locator('flt-semantics:has-text("Continue with Google")')
        .last();
    if (await google.count()) {
      const box = await google.boundingBox();
      if (box) {
        await this.page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
        await this.page.waitForTimeout(800);
      }
    }
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

  /** Click a nav-rail destination by its label. Uses a real coordinate click on
   *  the semantic node's box (Flutter ignores DOM clicks on the canvas). */
  async navigateTo(navLabel: string): Promise<void> {
    const button = this.page
      .locator(`flt-semantics[role="button"]:has-text("${navLabel}")`)
      .last();
    const box = await button.boundingBox();
    if (box) {
      await this.page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    }
    await this.page.waitForTimeout(600);
  }

  pill(which: "LIVE" | "SEED"): Locator {
    return this.byLabel(which);
  }
}
