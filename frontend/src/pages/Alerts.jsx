import { useCallback, useEffect, useState } from "react";
import {
  FiBell,
  FiCheck,
  FiMail,
  FiMessageSquare,
  FiRefreshCw,
  FiShield,
} from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import { Pagination } from "../components/DashboardComponents.jsx";
import AlertStatus from "../components/alerts/AlertStatus.jsx";
import {
  getAlertHistory,
  getAlertSettings,
  sendPredictionAlerts,
  updateAlertSettings,
} from "../services/alertService.js";
import { retryDetectionAlerts } from "../services/detectionService.js";
import "../styles/alerts.css";

const EMPTY_PAGE = {
  items: [],
  pagination: { page: 1, total_pages: 0, total_items: 0 },
};

const DEFAULT_SETTINGS = {
  email_alerts: true,
  sms_alerts: false,
  daily_notifications: false,
  high_risk_notifications: true,
  weather_alerts: true,
};

const SETTING_ROWS = [
  {
    key: "email_alerts",
    title: "Email Alerts",
    description: "Send eligible alerts to the email address on your profile.",
    icon: FiMail,
  },
  {
    key: "sms_alerts",
    title: "SMS Alerts",
    description: "Send eligible alerts to the verified phone number on your profile.",
    icon: FiMessageSquare,
  },
  {
    key: "high_risk_notifications",
    title: "Risk Threshold",
    description: "Send risk alerts when a climate risk assessment is High or Very High.",
    icon: FiShield,
  },
  {
    key: "daily_notifications",
    title: "Daily Notifications",
    description: "Receive a daily email summary of recent activity at 09:00 UTC.",
    icon: FiBell,
  },
  {
    key: "weather_alerts",
    title: "Weather Alerts",
    description: "Include alerts for configured high-humidity and rainfall conditions.",
    icon: FiBell,
  },
];

export default function Alerts() {
  const [result, setResult] = useState(EMPTY_PAGE);
  const [filters, setFilters] = useState({
    type: "",
    status: "",
    start_date: "",
    end_date: "",
  });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");
  const [notice, setNotice] = useState("");
  const [retrying, setRetrying] = useState("");
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [settingsLoading, setSettingsLoading] = useState(true);
  const [settingsError, setSettingsError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setHistoryError("");
    try {
      setResult(await getAlertHistory({
        page,
        per_page: 20,
        type: filters.type || undefined,
        status: filters.status || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined,
      }));
    } catch (error) {
      setHistoryError(error.response?.data?.message || "Alert history could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    let active = true;
    getAlertSettings()
      .then((preferences) => {
        if (active) setSettings({ ...DEFAULT_SETTINGS, ...preferences });
      })
      .catch((error) => {
        if (active) {
          setSettingsError(error.response?.data?.message || "Alert preferences could not be loaded.");
        }
      })
      .finally(() => {
        if (active) setSettingsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function changeFilter(key, value) {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  }

  async function retry(alert) {
    const target = alert.prediction_id
      ? `prediction:${alert.prediction_id}`
      : `detection:${alert.mosquito_detection_id}`;
    setRetrying(target);
    setNotice("");
    setHistoryError("");
    try {
      const response = alert.prediction_id
        ? await sendPredictionAlerts(alert.prediction_id)
        : await retryDetectionAlerts(alert.mosquito_detection_id);
      setNotice(response.message);
      await loadHistory();
    } catch (error) {
      setHistoryError(error.response?.data?.message || "The alert could not be retried.");
    } finally {
      setRetrying("");
    }
  }

  async function saveSettings() {
    setSaving(true);
    setSettingsError("");
    setSaved(false);
    try {
      setSettings(await updateAlertSettings(settings));
      setSaved(true);
    } catch (error) {
      setSettingsError(error.response?.data?.message || "Alert preferences could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="dashboard-page">
      <div className="page-intro">
        <span className="page-overline">NOTIFICATIONS</span>
        <h2>Alerts</h2>
        <p>Review recent alert activity and manage how you receive notifications.</p>
      </div>

      <section className="surface-card alert-history-card">
        <div className="surface-heading">
          <div>
            <h2>Alert History</h2>
            <p>{result.pagination.total_items} records</p>
          </div>
          <button
            type="button"
            className="btn btn-outline-primary btn-sm"
            onClick={loadHistory}
            disabled={loading}
          >
            <FiRefreshCw className="me-1" />Refresh
          </button>
        </div>
        {historyError && <AlertMessage message={historyError} />}
        {notice && <AlertMessage message={notice} variant="success" onDismiss={() => setNotice("")} />}
        <div className="alert-toolbar">
          <div className="alert-filters">
            <label>
              <span>Channel</span>
              <select
                className="form-select"
                value={filters.type}
                onChange={(event) => changeFilter("type", event.target.value)}
              >
                <option value="">All channels</option>
                <option value="email">Email</option>
                <option value="sms">SMS</option>
                <option value="in_app">In-app</option>
              </select>
            </label>
            <label>
              <span>Status</span>
              <select
                className="form-select"
                value={filters.status}
                onChange={(event) => changeFilter("status", event.target.value)}
              >
                <option value="">All statuses</option>
                <option value="queued">Queued</option>
                <option value="retrying">Retrying</option>
                <option value="sent">Success</option>
                <option value="failed">Failed</option>
              </select>
            </label>
            <label>
              <span>From</span>
              <input
                className="form-control"
                type="date"
                value={filters.start_date}
                onChange={(event) => changeFilter("start_date", event.target.value)}
              />
            </label>
            <label>
              <span>To</span>
              <input
                className="form-control"
                type="date"
                value={filters.end_date}
                onChange={(event) => changeFilter("end_date", event.target.value)}
              />
            </label>
          </div>
        </div>
        {loading ? (
          <p role="status" className="text-secondary">Loading alerts…</p>
        ) : result.items.length ? (
          <div className="table-responsive">
            <table className="table align-middle alert-table">
              <thead>
                <tr>
                  <th>Alert</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Recipient</th>
                  <th>Message preview</th>
                  <th><span className="visually-hidden">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((alert) => {
                  const retryTarget = alert.prediction_id
                    ? `prediction:${alert.prediction_id}`
                    : `detection:${alert.mosquito_detection_id}`;
                  const canRetry = alert.status === "failed"
                    && (alert.prediction_id || alert.mosquito_detection_id);
                  return (
                    <tr key={alert.id}>
                      <td className="text-capitalize">{alert.alert_type}</td>
                      <td>{new Date(alert.sent_at || alert.created_at).toLocaleString()}</td>
                      <td><AlertStatus status={alert.status} type={alert.alert_type} /></td>
                      <td>{alert.recipient}</td>
                      <td className="alert-preview">{alert.message_preview}</td>
                      <td>
                        {canRetry && (
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => retry(alert)}
                            disabled={retrying === retryTarget}
                          >
                            {retrying === retryTarget ? "Retrying…" : "Retry"}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="alert-empty">
            <FiBell /><strong>No alerts found</strong>
            <span>Alert activity matching these filters will appear here.</span>
          </div>
        )}
        <Pagination
          page={result.pagination.page || 1}
          pageCount={result.pagination.total_pages || 0}
          onChange={setPage}
        />
      </section>

      <section className="surface-card settings-page-card alert-preferences-card mt-4">
        <div className="surface-heading">
          <div>
            <h2>Alert Preferences</h2>
            <p>Choose which supported notifications to receive.</p>
          </div>
        </div>
        {settingsError && <AlertMessage message={settingsError} />}
        {settingsLoading ? (
          <p role="status">Loading alert preferences…</p>
        ) : (
          <>
            {SETTING_ROWS.slice(0, 2).map((row) => (
              <PreferenceRow
                key={row.key}
                row={row}
                checked={settings[row.key]}
                disabled={saving}
                onChange={(checked) => {
                  setSaved(false);
                  setSettings((current) => ({ ...current, [row.key]: checked }));
                }}
              />
            ))}
            <PreferenceRow
              row={{
                key: "push_notifications",
                title: "Push Notifications",
                description: "Browser push is not available in the current alert service.",
                icon: FiBell,
              }}
              checked={false}
              disabled
            />
            {SETTING_ROWS.slice(2).map((row) => (
              <PreferenceRow
                key={row.key}
                row={row}
                checked={settings[row.key]}
                disabled={saving}
                onChange={(checked) => {
                  setSaved(false);
                  setSettings((current) => ({ ...current, [row.key]: checked }));
                }}
              />
            ))}
            <div className="settings-privacy-note">
              <FiShield />
              <span>
                <strong>Your contact details stay private</strong>
                <small>Email and phone alerts use the contact details saved in your profile.</small>
              </span>
            </div>
            <button
              className="btn btn-primary mt-4"
              type="button"
              onClick={saveSettings}
              disabled={settingsLoading || saving || Boolean(settingsError)}
            >
              {saving ? "Saving…" : "Save Settings"}
            </button>
            {saved && (
              <p className="small text-success mt-2 mb-0" role="status">
                <FiCheck className="me-1" />Alert preferences saved.
              </p>
            )}
          </>
        )}
      </section>
    </div>
  );
}

function PreferenceRow({ row, checked, disabled = false, onChange }) {
  const Icon = row.icon;
  return (
    <div className="preference-row">
      <span className="feature-icon feature-icon-teal"><Icon aria-hidden="true" /></span>
      <span className="preference-copy">
        <strong>{row.title}</strong>
        <small>{row.description}</small>
      </span>
      <div className="form-check form-switch">
        <input
          className="form-check-input"
          type="checkbox"
          role="switch"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange?.(event.target.checked)}
          aria-label={row.title}
        />
      </div>
    </div>
  );
}
