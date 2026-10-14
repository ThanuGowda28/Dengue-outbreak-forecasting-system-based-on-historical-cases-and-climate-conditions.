import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  AUTH_UNAUTHORIZED_EVENT,
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  TOKEN_REFRESHED_EVENT
} from "../services/api.js";
import * as authService from "../services/authService.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_TOKEN_KEY));
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    setAccessToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      clearSession();
    };
    const handleTokenRefreshed = () => {
      setAccessToken(localStorage.getItem(ACCESS_TOKEN_KEY));
    };
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    window.addEventListener(TOKEN_REFRESHED_EVENT, handleTokenRefreshed);
    return () => {
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
      window.removeEventListener(TOKEN_REFRESHED_EVENT, handleTokenRefreshed);
    };
  }, []);

  useEffect(() => {
    let active = true;
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return () => { active = false; };
    }
    setAccessToken(token);
    authService.getProfile()
      .then((profile) => {
        if (active) setUser(profile);
      })
      .catch(() => {
        if (active) clearSession();
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [clearSession]);

  const saveAuthResponse = useCallback((response) => {
    if (response.access_token) {
      localStorage.setItem(ACCESS_TOKEN_KEY, response.access_token);
      setAccessToken(response.access_token);
    }
    if (response.refresh_token) localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token);
    setUser(response.user || null);
    return response;
  }, []);

  const login = useCallback(async (credentials) => saveAuthResponse(await authService.login(credentials)), [saveAuthResponse]);
  const adminLogin = useCallback(async (credentials) => saveAuthResponse(await authService.adminLogin(credentials)), [saveAuthResponse]);
  const register = useCallback((details) => authService.register(details), []);
  const updateProfile = useCallback(async (details) => {
    const updated = await authService.updateProfile(details);
    setUser(updated);
    return updated;
  }, []);
  const changePassword = useCallback((payload) => authService.changePassword(payload), []);
  const refresh = useCallback(async () => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) {
      clearSession();
      throw new Error("Your session has expired. Please sign in again.");
    }
    try {
      const response = await authService.refreshAccessToken(refreshToken);
      saveAuthResponse({ ...response, user });
      return response;
    } catch (error) {
      clearSession();
      throw error;
    }
  }, [clearSession, saveAuthResponse, user]);
  const logout = useCallback(async () => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    try {
      if (refreshToken) await authService.logout(refreshToken);
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo(() => ({
    user,
    accessToken,
    isAuthenticated: Boolean(user && accessToken),
    loading,
    login,
    adminLogin,
    logout,
    register,
    updateProfile,
    changePassword,
    refresh
  }), [user, accessToken, loading, login, adminLogin, logout, register, updateProfile, changePassword, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
