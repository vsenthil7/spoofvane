// v06 §A — runnable unit test for the pure sidebar heuristic.
// Runs under plain Node 24 (type-stripping), no browser/build needed:
//   node --test src/lib/sidebar-logic.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  shouldAutoCollapse,
  railWidth,
  RAIL_W_EXPANDED,
  RAIL_W_COLLAPSED,
} from "./sidebar-logic.ts";

test("railWidth maps collapsed state to px", () => {
  assert.equal(railWidth(false), RAIL_W_EXPANDED);
  assert.equal(railWidth(true), RAIL_W_COLLAPSED);
  assert.equal(railWidth(true), 64);
});

test("responsive: narrow viewport always auto-collapses", () => {
  assert.equal(shouldAutoCollapse("/", 800), true);
  assert.equal(shouldAutoCollapse("/", 1023), true);
});

test("route-aware: detail/queue routes auto-collapse on wide screens", () => {
  assert.equal(shouldAutoCollapse("/triage", 1600), true);
  assert.equal(shouldAutoCollapse("/review", 1600), true);
  assert.equal(shouldAutoCollapse("/alerts/abc123", 1600), true);
});

test("negative: normal route on a wide screen does NOT auto-collapse", () => {
  assert.equal(shouldAutoCollapse("/", 1600), false);
  assert.equal(shouldAutoCollapse("/brands", 1440), false);
  assert.equal(shouldAutoCollapse("/cost", 1280), false);
});

test("boundary: exactly 1024 is wide enough (not collapsed by width alone)", () => {
  assert.equal(shouldAutoCollapse("/", 1024), false);
});
