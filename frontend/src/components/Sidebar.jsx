import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Activity,
  Bell,
  ChartNoAxesCombined,
  ChevronLeft,
  CloudSun,
  Database,
  FileText,
  HeartPulse,
  History,
  LayoutDashboard,
  LogOut,
  Map,
  PanelLeftClose,
  Settings,
  Users,
  UserRound,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

const userItems = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  { label: "Climate Risk Assessment", to: "/prediction", icon: ChartNoAxesCombined },
  { label: "Forecasting", to: "/forecasting", icon: ChartNoAxesCombined },
  { label: "Weather", to: "/weather", icon: CloudSun },
  { label: "Risk Map", to: "/risk-map", icon: Map },
  { label: "Hospital Finder", to: "/hospitals", icon: HeartPulse },
  { label: "History", to: "/history", icon: History },
  { label: "Alerts", to: "/alerts", icon: Bell },
  { label: "Profile", to: "/profile", icon: UserRound },
  { label: "Settings", to: "/settings", icon: Settings }
];

const adminItems = [
  { label: "Dashboard", to: "/admin/dashboard", icon: LayoutDashboard },
  { label: "Climate Risk Assessment", to: "/prediction", icon: ChartNoAxesCombined },
  { label: "Forecasting", to: "/forecasting", icon: ChartNoAxesCombined },
  { label: "Weather", to: "/weather", icon: CloudSun },
  { label: "Risk Map", to: "/risk-map", icon: Map },
  { label: "Hospital Finder", to: "/hospitals", icon: HeartPulse },
  { label: "History", to: "/history", icon: History },
  { label: "Alerts", to: "/alerts", icon: Bell },
  { label: "Profile", to: "/profile", icon: UserRound },
  { label: "Settings", to: "/settings", icon: Settings },
  { label: "Manage users", to: "/users", icon: Users },
  { label: "Risk Assessments", to: "/admin/predictions", icon: ChartNoAxesCombined },
  { label: "Manage datasets", to: "/datasets", icon: Database },
  { label: "Climate data", to: "/climate-data", icon: CloudSun },
  { label: "Research tools", to: "/train-model", icon: ChartNoAxesCombined },
  { label: "Reports", to: "/reports", icon: FileText },
  { label: "Alert management", to: "/admin/alerts", icon: Bell },
  { label: "Hospital management", to: "/admin/hospitals", icon: HeartPulse }
];

export default function Sidebar({ mobileOpen = false, onNavigate }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const isAdmin = user?.role?.toLowerCase() === "admin";
  const items = isAdmin ? adminItems : userItems;

  async function handleLogout() {
    try {
      await logout();
    } finally {
      navigate("/", { replace: true });
    }
  }

  return (
    <aside className={`dashboard-sidebar ${mobileOpen ? "dashboard-sidebar-open" : ""} ${collapsed ? "dashboard-sidebar-collapsed" : ""}`}>
      <div className="sidebar-brand-row">
        <NavLink to="/" className="sidebar-brand" onClick={onNavigate} title="DengueWatch home">
          <span className="brand-mark"><Activity size={20} aria-hidden="true" /></span>
          <span className="sidebar-brand-copy">Dengue<span className="brand-accent">Watch</span><small>HEALTH FORECASTING</small></span>
        </NavLink>
        <button
          type="button"
          className="sidebar-collapse-toggle"
          onClick={() => setCollapsed((value) => !value)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeftClose size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>
      <p className="sidebar-label">{isAdmin ? "ADMIN WORKSPACE" : "YOUR WORKSPACE"}</p>
      <nav className="sidebar-nav" aria-label="Dashboard navigation">
        {items.map(({ label, to, icon: Icon }) => (
          <NavLink key={to} to={to} end title={collapsed ? label : undefined} aria-label={label} className={({ isActive }) => `sidebar-link ${isActive ? "active" : ""}`} onClick={onNavigate}>
            <Icon size={18} strokeWidth={1.8} aria-hidden="true" /><span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-help"><span className="sidebar-help-icon"><Activity size={17} aria-hidden="true" /></span><strong>Stay informed</strong><p>Forecasts are informational and are not a medical diagnosis.</p></div>
        <button type="button" className="sidebar-link sidebar-logout" onClick={handleLogout} title={collapsed ? "Log out" : undefined}><LogOut size={18} aria-hidden="true" /><span>Log out</span></button>
      </div>
    </aside>
  );
}
