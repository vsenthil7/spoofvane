// v06 §C — runnable unit test for the seed lane data integrity.
// node --test src/lib/seed.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  SEED, SEED_ALERTS, SEED_BRANDS, seedRespectsThresholds,
} from "./seed.ts";

test("seed values respect real scoring thresholds", () => {
  // Above brand threshold => non-benign; below => benign. Plausible, not arbitrary.
  assert.equal(seedRespectsThresholds(), true);
});

test("every wrapped api method has a seed fallback", () => {
  const methods = [
    "listBrands", "getBrand", "triageQueue", "getAlert",
    "clusters", "deepfakes", "audit", "reviewQueue", "cost",
  ];
  for (const m of methods) {
    assert.ok(m in SEED, `missing seed for ${m}`);
  }
});

test("triage queue seed excludes benign (negative case)", () => {
  const triage = SEED["triageQueue"] as typeof SEED_ALERTS;
  assert.ok(triage.length > 0);
  assert.ok(triage.every(a => a.verdict !== "benign"));
});

test("a known seeded alert id is present for the offline render assertion", () => {
  assert.ok(SEED_ALERTS.some(a => a.id === "alert_seed_001"));
  assert.ok(SEED_BRANDS.some(b => b.id === "brand_acmebank"));
});
