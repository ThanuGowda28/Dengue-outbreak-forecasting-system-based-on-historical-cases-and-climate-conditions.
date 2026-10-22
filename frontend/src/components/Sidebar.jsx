import { NavLink, useNavigate } from "react-router-dom";
import {
  FiActivity,
  FiBell,
  FiCloud,
  FiDatabase,
  FiFileText,
  FiGrid,
  FiSearch,
  FiLogOut,
  FiMap,
  FiHeart,
  FiSettings,
  FiTarget,
  FiUsers
} from "react-icons/fi";
import { useAuth } from "../context/AuthContext.jsx";

const userItems = [
  { label: "Dashboard", to: "/dashboard", icon: FiGrid },
  { label: "Prediction", to: "/prediction", icon: FiTarget },
  { label: "Weather", to: "/weather", icon: FiCloud },
  { label: "Risk map", to: "/risk-map", icon: FiMap },
  { label: "Hospital finder", to: "/hospital-finder", icon: FiHeart },
  { label: "Mosquito detection", to: "/mosquito-detection", icon: FiSearch },
  { label: "Detection history", to: "/mosquito-detection/history", icon: FiActivity },
  { label: "History", to: "/history", icon: FiActivity },
  { label: "Alert history", to: "/alerts", icon: FiBell },
  { label: "Alert settings", to: "/alert-settings", icon: FiSettings },
  { label: "Profile", to: "/profile", icon: FiUsers },
  { label: "Settings", to: "/settings", icon: FiSettings }
];

const adminItems = [
  { label: "Dashboard", to: "/admin/dashboard", icon: FiGrid },
  { label: "Manage users", to: "/users", icon: FiUsers },
  { label: "Predictions", to: "/admin/predictions", icon: FiTarget },
  { label: "Manage datasets", to: "/datasets", icon: FiDatabase },
  { label: "Climate data", to: "/climate-data", icon: FiCloud },
  { label: "Train model", to: "/train-model", icon: FiTarget },
  { label: "Reports", to: "/reports", icon: FiFileText },
  { label: "Alert management", to: "/admin/alerts", icon: FiBell },
  { label: "Mosquito detection reports", to: "/admin/mosquito-detection", icon: FiSearch },
  { label: "Hospital management", to: "/admin/hospitals", icon: FiHeart },
  { label: "Settings", to: "/settings", icon: FiSettings }
];

export default function Sidebar({ mobileOpen = false, onNavigate }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
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
    <aside className={`dashboard-sidebar ${mobileOpen ? "dashboard-sidebar-open" : ""}`}>
      <NavLink to="/" className="sidebar-brand" onClick={onNavigate}>
        <span className="brand-mark"><FiActivity /></span>
        <span>Dengue<span className="brand-accent">Watch</span><small>HEALTH INTELLIGENCE</small></span>
      </NavLink>
      <p className="sidebar-label">{isAdmin ? "ADMIN WORKSPACE" : "YOUR WORKSPACE"}</p>
      <nav className="sidebar-nav" aria-label="Dashboard navigation">
        {items.map(({ label, to, icon: Icon }) => (
          <NavLink key={to} to={to} end className={({ isActive }) => `sidebar-link ${isActive ? "active" : ""}`} onClick={onNavigate}>
            <Icon aria-hidden="true" /><span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-help"><span className="sidebar-help-icon"><FiActivity /></span><strong>Stay informed</strong><p>Forecasts are informational and are not a medical diagnosis.</p></div>
        <button type="button" className="sidebar-link sidebar-logout" onClick={handleLogout}><FiLogOut aria-hidden="true" /><span>Log out</span></button>
      </div>
    </aside>
  );
}
