export const API_UNAVAILABLE_MESSAGE =
  "We’re having trouble connecting right now. Please try again in a moment.";

const TECHNICAL_MESSAGE_PATTERN =
  /\b(flask|openweather|redis|mysql|sqlalchemy|stack trace|traceback|internal server error|http\s?\d{3}|api (?:endpoint|url)|https?:\/\/|127\.0\.0\.1|localhost:\d|OPENWEATHER_API_KEY|\.env|model path|database connection)\b/i;

export function sanitizeUserMessage(message, fallback = "We couldn’t complete that request. Please try again.") {
  if (typeof message !== "string" || !message.trim()) return fallback;
  return TECHNICAL_MESSAGE_PATTERN.test(message) ? fallback : message;
}

export function normalizeTransportError(error) {
  if (!error.response && error.code !== "ERR_CANCELED") {
    error.message = API_UNAVAILABLE_MESSAGE;
  } else if (typeof error.response?.data?.message === "string") {
    error.response.data.message = sanitizeUserMessage(error.response.data.message);
  }
  return error;
}

export function getApiErrorMessage(error, fallback) {
  if (error?.response?.data?.message) return sanitizeUserMessage(error.response.data.message, fallback);
  if (
    !error?.response &&
    (error?.code === "ERR_NETWORK" ||
      error?.message === "Network Error" ||
      error?.request)
  ) {
    return API_UNAVAILABLE_MESSAGE;
  }
  return sanitizeUserMessage(error?.message, fallback);
}
