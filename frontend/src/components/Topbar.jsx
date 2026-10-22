import { useState } from "react";
import { FiMenu, FiMoon, FiSun } from "react-icons/fi";
import { useAuth } from "../context/AuthContext.jsx";
import NotificationBadge from "./NotificationBadge.jsx";

export default function Topbar({
  title,
  onMenu,
  darkMode = false,
  onToggleTheme,
  themeDisabled = false
}) {
  const { user } = useAuth();

  return (
    <header className="dashboard-topbar">
      <button type="button" className="icon-button dashboard-menu-toggle" onClick={onMenu} aria-label="Open dashboard menu"><FiMenu /></button>
      <div className="topbar-title"><span className="topbar-date">DENGUEWATCH / WORKSPACE</span><h1>{title}</h1></div>
      <div className="topbar-actions">
        <button type="button" className="icon-button" onClick={onToggleTheme} disabled={themeDisabled} aria-label={darkMode ? "Switch to light theme" : "Switch to dark theme"} title="Display theme">
          {darkMode ? <FiSun /> : <FiMoon />}
        </button>
        <NotificationBadge />
        <div className="topbar-user"><span className="user-avatar">{(user?.full_name || "User").slice(0, 1).toUpperCase()}</span><span><strong>{user?.full_name || "Welcome"}</strong><small>{user?.role === "admin" ? "Administrator" : "Registered user"}</small></span></div>
      </div>
    </header>
  );
}
