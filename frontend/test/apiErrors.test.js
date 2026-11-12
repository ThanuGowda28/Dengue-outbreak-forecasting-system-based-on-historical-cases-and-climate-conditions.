import test from "node:test";
import assert from "node:assert/strict";

import {
  API_UNAVAILABLE_MESSAGE,
  getApiErrorMessage,
  normalizeTransportError,
  sanitizeUserMessage
} from "../src/utils/apiErrors.js";

test("network errors receive a friendly retry message", () => {
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

test("technical provider and server details are replaced with a friendly message", () => {
  const error = {
    response: {
      data: { message: "Flask returned HTTP 500 from http://127.0.0.1:5000/api/weather." }
    }
  };
  normalizeTransportError(error);
  assert.equal(error.response.data.message, "We couldn’t complete that request. Please try again.");
  assert.equal(
    sanitizeUserMessage("OPENWEATHER_API_KEY is missing."),
    "We couldn’t complete that request. Please try again."
  );
});
