import test from "node:test";
import assert from "node:assert/strict";

import { normalizeRiskTone } from "../src/utils/risk.js";

test("normalizes supported risk labels for display", () => {
  assert.equal(normalizeRiskTone("Low"), "low");
  assert.equal(normalizeRiskTone(" MODERATE "), "moderate");
  assert.equal(normalizeRiskTone("high"), "high");
});

test("uses a neutral tone for absent or unsupported labels", () => {
  assert.equal(normalizeRiskTone(""), "unknown");
  assert.equal(normalizeRiskTone(null), "unknown");
  assert.equal(normalizeRiskTone("Critical"), "unknown");
});
