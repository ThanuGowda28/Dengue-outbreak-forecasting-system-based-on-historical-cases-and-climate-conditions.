export const API_UNAVAILABLE_MESSAGE =
  "Cannot reach the Flask API. Start the backend at http://127.0.0.1:5000 and try again.";

export function normalizeTransportError(error) {
  if (!error.response && error.code !== "ERR_CANCELED") {
    error.message = API_UNAVAILABLE_MESSAGE;
  }
  return error;
}

export function getApiErrorMessage(error, fallback) {
  if (error?.response?.data?.message) return error.response.data.message;
  if (
    !error?.response &&
    (error?.code === "ERR_NETWORK" ||
      error?.message === "Network Error" ||
      error?.request)
  ) {
    return API_UNAVAILABLE_MESSAGE;
  }
  return error?.message || fallback;
}
