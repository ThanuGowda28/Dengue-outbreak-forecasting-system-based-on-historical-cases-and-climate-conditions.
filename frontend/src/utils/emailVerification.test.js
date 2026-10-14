import assert from "node:assert/strict";
import test from "node:test";
import {
  isValidVerificationEmail,
  parseEmailVerificationQuery,
  verificationErrorMessage
} from "./emailVerification.js";

test("parses the verification token from the email link", () => {
  assert.deepEqual(parseEmailVerificationQuery("?token=abc123"), {
    token: "abc123",
    email: ""
  });
});

test("parses an optional email and handles an empty query", () => {
  assert.deepEqual(parseEmailVerificationQuery("?email=person%40example.test"), {
    token: "",
    email: "person@example.test"
  });
  assert.deepEqual(parseEmailVerificationQuery(""), { token: "", email: "" });
});

test("validates resend addresses", () => {
  assert.equal(isValidVerificationEmail(" person@example.test "), true);
  assert.equal(isValidVerificationEmail("not-an-email"), false);
  assert.equal(isValidVerificationEmail(null), false);
});

test("surfaces invalid and expired verification-link responses", () => {
  assert.equal(
    verificationErrorMessage({
      response: { data: { message: "Verification link has expired. Request a new link." } }
    }),
    "Verification link has expired. Request a new link."
  );
  assert.equal(
    verificationErrorMessage({ response: { data: { message: "Verification link is invalid or has already been used." } } }),
    "Verification link is invalid or has already been used."
  );
  assert.equal(verificationErrorMessage(new Error("network failure")), "The verification link could not be confirmed.");
  assert.equal(
    verificationErrorMessage(new Error("network failure"), "A verification email could not be requested."),
    "A verification email could not be requested."
  );
});
