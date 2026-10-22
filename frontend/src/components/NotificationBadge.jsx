import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FiBell } from "react-icons/fi";
import { getAlertHistory } from "../services/alertService.js";
import AlertStatus from "./alerts/AlertStatus.jsx";

export default function NotificationBadge() {
  const [alerts, setAlerts] = useState([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const result = await getAlertHistory({ page: 1, per_page: 5 });
        if (active) {
          setAlerts(result.items);
          setError("");
        }
      } catch (loadError) {
        if (active) {
          setError(loadError.response?.data?.message || "Notifications could not be loaded.");
        }
      }
    }
    refresh();
    const timer = window.setInterval(refresh, 20000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const pendingCount = alerts.filter((alert) =>
    ["queued", "sending", "retrying"].includes(alert.status)
    || (alert.alert_type === "in_app" && Date.now() - new Date(alert.created_at).getTime() < 24 * 60 * 60 * 1000)
  ).length;
  return (
    <div className="notification-wrap">
      <button type="button" className="icon-button notification-button" onClick={() => setOpen((value) => !value)} aria-label={`Notifications${pendingCount ? `, ${pendingCount} pending` : ""}`} aria-expanded={open}>
        <FiBell />
        {pendingCount > 0 && <span className="notification-count">{pendingCount > 9 ? "9+" : pendingCount}</span>}
      </button>
      {open && (
        <div className="notification-popover alert-notification-popover">
          <strong>Recent alerts</strong>
          {error ? <span role="status">{error}</span> : alerts.length ? alerts.slice(0, 4).map((alert) => (
            <div className="notification-alert-row" key={alert.id}>
              <AlertStatus status={alert.status} type={alert.alert_type} />
              <small>{new Date(alert.sent_at || alert.created_at).toLocaleString()}</small>
            </div>
          )) : <span>No recent alert activity.</span>}
          <Link to="/alerts" onClick={() => setOpen(false)}>View alert history</Link>
        </div>
      )}
    </div>
  );
}
