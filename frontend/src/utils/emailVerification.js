import { EMAIL_PATTERN } from "./authValidation.js";

export function parseEmailVerificationQuery(search) {
  const query = new URLSearchParams(search);
  return {
    token: query.get("token")?.trim() || "",
    email: query.get("email")?.trim() || ""
  };
}

export function isValidVerificationEmail(email) {
  return typeof email === "string" && EMAIL_PATTERN.test(email.trim());
}

export function verificationErrorMessage(error, fallback = "The verification link could not be confirmed.") {
  const message = error?.response?.data?.message;
  return typeof message === "string" && message.trim()
    ? message
    : fallback;
}
