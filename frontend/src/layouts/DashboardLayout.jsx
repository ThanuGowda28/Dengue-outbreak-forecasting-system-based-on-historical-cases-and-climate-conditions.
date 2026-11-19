import { useCallback, useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import Sidebar from "../components/Sidebar.jsx";
import Topbar from "../components/Topbar.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getSettings, updateSettings } from "../services/authService.js";

const DEFAULT_PREFERENCES = {
  alerts: true,
  weekly_summary: false,
  dark_mode: false
};

const pageTitles = {
  "/dashboard": "Your dashboard",
  "/admin/dashboard": "Administration",
  "/prediction": "Prediction",
  "/forecasting": "AI forecast",
  "/weather": "Local weather",
  "/risk-map": "Community risk map",
  "/hospitals": "Hospital finder",
  "/history": "History",
  "/alerts": "Alerts",
  "/admin/alerts": "Alert management",
  "/admin/mosquito-detection": "Mosquito detection reports",
  "/profile": "Your profile",
  "/settings": "Settings",
  "/users": "Manage users",
  "/datasets": "Manage datasets",
  "/climate-data": "Climate data",
  "/train-model": "Research tools",
  "/reports": "Reports"
};

export default function DashboardLayout() {
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [settingsLoading, setSettingsLoading] = useState(true);
  const [settingsError, setSettingsError] = useState("");
  const location = useLocation();
  const title = location.pathname === "/dashboard" && user?.role?.toLowerCase() === "admin"
    ? "Administration"
    : pageTitles[location.pathname] || "Workspace";

  const loadPreferences = useCallback(async () => {
    setSettingsLoading(true);
    setSettingsError("");
    try {
      const loaded = await getSettings();
      setPreferences(loaded);
      document.documentElement.dataset.theme = loaded.dark_mode ? "dark" : "light";
    } catch (error) {
      setSettingsError(
        error.response?.data?.message || "Saved preferences could not be loaded."
      );
    } finally {
      setSettingsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  const changePreference = useCallback((name, value) => {
    setPreferences((current) => {
      const next = { ...current, [name]: value };
      if (name === "dark_mode") {
        document.documentElement.dataset.theme = value ? "dark" : "light";
      }
      return next;
    });
  }, []);

  const savePreferences = useCallback(async (next) => {
    const stored = await updateSettings(next);
    setPreferences(stored);
    document.documentElement.dataset.theme = stored.dark_mode ? "dark" : "light";
    setSettingsError("");
    return stored;
  }, []);

  return (
    <div className="dashboard-app">
      {menuOpen && <button className="dashboard-scrim" type="button" aria-label="Close dashboard menu" onClick={() => setMenuOpen(false)} />}
      <Sidebar mobileOpen={menuOpen} onNavigate={() => setMenuOpen(false)} />
      <div className="dashboard-main">
        <Topbar
          title={title}
          onMenu={() => setMenuOpen(true)}
          darkMode={preferences.dark_mode}
          onToggleTheme={() => changePreference("dark_mode", !preferences.dark_mode)}
          themeDisabled={settingsLoading || Boolean(settingsError)}
        />
        <div className="dashboard-content">
          <motion.div
            key={location.pathname}
            className="dashboard-route-content"
            initial={{ opacity: 0, y: 7 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
          >
            <Outlet context={{
              preferences,
              changePreference,
              savePreferences,
              loadPreferences,
              settingsLoading,
              settingsError
            }} />
          </motion.div>
        </div>
      </div>
    </div>
  );
}
