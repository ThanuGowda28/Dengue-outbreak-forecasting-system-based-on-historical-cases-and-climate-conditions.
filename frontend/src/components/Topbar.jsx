import { useState } from "react";
import { Link } from "react-router-dom";
import { MapPin, Menu, Moon, Sun } from "lucide-react";
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
  const location = [user?.district, user?.state].filter(Boolean).join(", ");

  return (
    <header className="dashboard-topbar">
      <button type="button" className="icon-button dashboard-menu-toggle" onClick={onMenu} aria-label="Open dashboard menu"><Menu size={20} /></button>
      <div className="topbar-title"><span className="topbar-date">DENGUEWATCH / HEALTH FORECASTING</span><h1>{title}</h1></div>
      <div className="topbar-actions">
        {location && <span className="topbar-location"><MapPin size={15} aria-hidden="true" /><span>{location}</span></span>}
        <button type="button" className="icon-button" onClick={onToggleTheme} disabled={themeDisabled} aria-label={darkMode ? "Switch to light theme" : "Switch to dark theme"} title="Display theme">
          {darkMode ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <NotificationBadge />
        <Link to="/profile" className="topbar-user" aria-label="Open profile">
          <span className="user-avatar">{(user?.full_name || "User").slice(0, 1).toUpperCase()}</span>
          <span><strong>{user?.full_name || "Welcome"}</strong><small>{user?.role === "admin" ? "Administrator" : "Health profile"}</small></span>
        </Link>
      </div>
    </header>
  );
}
