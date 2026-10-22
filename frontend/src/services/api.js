import axios from "axios";
import { normalizeTransportError } from "../utils/apiErrors.js";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "/api";

export const ACCESS_TOKEN_KEY = "access_token";
export const REFRESH_TOKEN_KEY = "refresh_token";

export const AUTH_UNAUTHORIZED_EVENT = "auth:unauthorized";
export const TOKEN_REFRESHED_EVENT = "auth:token-refreshed";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

let refreshInFlight = null;

// Attach access token automatically, unless a custom Authorization header is explicitly supplied.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);

  if (!config.headers) {
    config.headers = {};
  }

  if (config.skipAuth) {
    return config;
  }

  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// Handle unauthorized responses by attempting a refresh before giving up.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    normalizeTransportError(error);
    const originalRequest = error.config;
    const isUnauthorized = error.response?.status === 401;

    if (isUnauthorized && !originalRequest?._retry && !originalRequest?.skipAuth) {
      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
      if (!refreshToken) {
        window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
        return Promise.reject(error);
      }

      try {
        originalRequest._retry = true;
        if (!refreshInFlight) {
          refreshInFlight = axios
            .post(
              `${API_BASE_URL}/auth/refresh`,
              {},
              {
                headers: {
                  Authorization: `Bearer ${refreshToken}`
                },
              }
            )
            .then((refreshResponse) => {
              const newAccessToken = refreshResponse.data?.access_token;
              const newRefreshToken = refreshResponse.data?.refresh_token;
              if (!newAccessToken || !newRefreshToken) {
                throw new Error("Refresh response did not include both tokens.");
              }
              localStorage.setItem(ACCESS_TOKEN_KEY, newAccessToken);
              localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);
              window.dispatchEvent(new Event(TOKEN_REFRESHED_EVENT));
              return newAccessToken;
            })
            .finally(() => {
              refreshInFlight = null;
            });
        }
        const newAccessToken = await refreshInFlight;
        if (originalRequest.url?.endsWith("/auth/logout")) {
          originalRequest.data = {
            refresh_token: localStorage.getItem(REFRESH_TOKEN_KEY),
          };
        }
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        normalizeTransportError(refreshError);
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
        return Promise.reject(refreshError);
      }
    }

    if (isUnauthorized) {
      window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
    }

    return Promise.reject(error);
  }
);

export default api;
