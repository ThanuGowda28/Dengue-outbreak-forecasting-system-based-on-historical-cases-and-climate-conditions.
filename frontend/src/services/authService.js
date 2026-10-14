import api from "./api.js";

export const register = (payload) =>
  api.post("/auth/register", payload, { skipAuth: true }).then(({ data }) => data);
export const login = (payload) =>
  api.post("/auth/login", payload, { skipAuth: true }).then(({ data }) => data);
export const adminLogin = (payload) =>
  api.post("/admin/auth/login", payload, { skipAuth: true }).then(({ data }) => data);
export const verifyEmail = (token) =>
  api.post("/auth/email-verification", { token }, { skipAuth: true }).then(({ data }) => data);
export const resendEmailVerification = (email) =>
  api.post("/auth/email-verification/resend", { email }, { skipAuth: true }).then(({ data }) => data);
export const getProfile = () => api.get("/auth/profile").then(({ data }) => data.user);
export const updateProfile = (payload) => api.put("/auth/profile", payload).then(({ data }) => data.user);
export const getSettings = () => api.get("/auth/settings").then(({ data }) => data.preferences);
export const updateSettings = (payload) =>
  api.put("/auth/settings", payload).then(({ data }) => data.preferences);
export const logout = (refreshToken) =>
  api.post("/auth/logout", { refresh_token: refreshToken }).then(({ data }) => data);
export const changePassword = (payload) => api.post("/auth/change-password", payload).then(({ data }) => data);
export const requestPasswordReset = (email) =>
  api.post("/auth/password-reset-request", { email }, { skipAuth: true }).then(({ data }) => data);
export const resetPassword = (payload) =>
  api.post("/auth/password-reset", payload, { skipAuth: true }).then(({ data }) => data);
export const refreshAccessToken = (refreshToken) =>
  api
    .post(
      "/auth/refresh",
      {},
      {
        skipAuth: true,
        headers: { Authorization: `Bearer ${refreshToken}` },
      }
    )
    .then(({ data }) => data);
