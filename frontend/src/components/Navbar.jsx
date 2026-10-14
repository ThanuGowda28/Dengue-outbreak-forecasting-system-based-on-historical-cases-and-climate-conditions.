import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { FiActivity, FiLogOut, FiUser } from "react-icons/fi";
import { useAuth } from "../context/AuthContext.jsx";
import AlertMessage from "./AlertMessage.jsx";

const userLinks = [
  ["Dashboard", "/dashboard"],
  ["Prediction", "/prediction"],
  ["Weather", "/weather"],
  ["Risk Map", "/risk-map"],
  ["History", "/history"]
];
const adminLinks = [
  ["Dashboard", "/dashboard"],
  ["Users", "/users"],
  ["Datasets", "/datasets"],
  ["Climate data", "/climate-data"],
  ["Train Model", "/train-model"],
  ["Reports", "/reports"],
  ["Settings", "/settings"]
];

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const navigate = useNavigate();
  const isAdmin = String(user?.role || "").toLowerCase() === "admin";

  async function handleLogout() {
    setExpanded(false);
    try {
      await logout();
      setLogoutError("");
    } catch {
      setLogoutError("You have been signed out on this device, but the server could not revoke the session. Please try signing in and out again.");
    } finally {
      navigate("/", { replace: true });
    }
  }

  const links = isAuthenticated ? (isAdmin ? adminLinks : userLinks) : [
    ["Home", "/"],
    ["About", "/about"],
    ["Symptoms", "/symptoms"],
    ["Prevention", "/prevention"],
    ["FAQ", "/faq"]
  ];

  return (
    <header className="site-header">
      {logoutError && (
        <div className="container pt-3">
          <AlertMessage message={logoutError} onDismiss={() => setLogoutError("")} />
        </div>
      )}
      <nav className="navbar navbar-expand-lg container">
        <Link className="navbar-brand brand-lockup" to="/" onClick={() => setExpanded(false)}>
          <span className="brand-mark"><FiActivity /></span>
          <span>Dengue<span className="brand-accent">Watch</span><small>COMMUNITY HEALTH INTELLIGENCE</small></span>
        </Link>
        <button
          className="navbar-toggler"
          type="button"
          aria-label="Toggle navigation"
          aria-expanded={expanded}
          onClick={() => setExpanded((open) => !open)}
        >
          <span className="navbar-toggler-icon" />
        </button>
        <div className={`collapse navbar-collapse ${expanded ? "show" : ""}`}>
          <div className="navbar-nav ms-auto align-items-lg-center">
            {links.map(([label, path]) => (
              <NavLink key={path} to={path} end={path === "/"} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} onClick={() => setExpanded(false)}>
                {label}
              </NavLink>
            ))}
            {isAuthenticated ? (
              <>
                <NavLink to="/profile" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} onClick={() => setExpanded(false)}>
                  <FiUser className="me-1" /> Profile
                </NavLink>
                <button className="btn btn-nav-logout" type="button" onClick={handleLogout}>
                  <FiLogOut className="me-2" />Log out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className="nav-link nav-login" onClick={() => setExpanded(false)}>Log in</NavLink>
                <Link to="/register" className="btn btn-primary btn-sm px-3 ms-lg-2" onClick={() => setExpanded(false)}>Create account</Link>
              </>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
}
