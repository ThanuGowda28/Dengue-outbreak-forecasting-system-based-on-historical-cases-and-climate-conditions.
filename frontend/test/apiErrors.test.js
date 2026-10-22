import test from "node:test";
import assert from "node:assert/strict";

import {
  API_UNAVAILABLE_MESSAGE,
  getApiErrorMessage,
  normalizeTransportError
} from "../src/utils/apiErrors.js";

test("network errors receive a useful local backend message", () => {
  assert.equal(
    getApiErrorMessage(new Error("Network Error"), "Request failed."),
    API_UNAVAILABLE_MESSAGE
  );

  const requestError = { code: "ERR_NETWORK", response: undefined };
  assert.equal(normalizeTransportError(requestError).message, API_UNAVAILABLE_MESSAGE);
});

test("API and page-specific errors are preserved", () => {
  assert.equal(
    getApiErrorMessage({ response: { data: { message: "Invalid credentials." } } }, "Request failed."),
    "Invalid credentials."
  );
  assert.equal(getApiErrorMessage(new Error("Request failed."), "Try again."), "Request failed.");
});
