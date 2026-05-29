import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  snapshotDir: "./e2e/__snapshots__",
  expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.05 } }, // ≤5% parity gate
  use: { viewport: { width: 1440, height: 900 } },
});
