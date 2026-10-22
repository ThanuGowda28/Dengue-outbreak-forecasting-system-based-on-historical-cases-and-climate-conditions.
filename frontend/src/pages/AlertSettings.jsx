import { useEffect, useState } from "react";
import { FiBell, FiCheck, FiMail, FiMessageSquare, FiShield } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import { getAlertSettings, updateAlertSettings } from "../services/alertService.js";
import "../styles/alerts.css";

const DEFAULTS = {
  email_alerts: true,
  sms_alerts: false,
  daily_notifications: false,
  high_risk_notifications: true,
  weather_alerts: true
};

const SETTINGS = [
  ["email_alerts", "Email alerts", "Email high-risk prediction alerts to your verified account address.", FiMail],
  ["sms_alerts", "SMS alerts", "Opt in to eligible SMS alerts sent to the phone number on your profile. SMS is off until you enable it.", FiMessageSquare],
  ["daily_notifications", "Daily notifications", "Receive a daily email summary of your recent predictions at 09:00 UTC.", FiBell],
  ["high_risk_notifications", "High-risk notifications", "Alert me when the model classifies a prediction as High or Very High.", FiShield],
  ["weather_alerts", "Weather-triggered alerts", "Also alert when humidity exceeds 80%, rainfall exceeds 100 mm, and confidence exceeds 80%.", FiBell]
];

export default function AlertSettings() {
  const [settings, setSettings] = useState(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;
    getAlertSettings()
      .then((preferences) => { if (active) setSettings({ ...DEFAULTS, ...preferences }); })
      .catch((loadError) => { if (active) setError(loadError.response?.data?.message || "Alert settings could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function save() {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      setSettings(await updateAlertSettings(settings));
      setSaved(true);
    } catch (saveError) {
      setError(saveError.response?.data?.message || "Alert settings could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">NOTIFICATION PREFERENCES</span><h2>Alert settings</h2><p>Choose how and when DengueWatch sends account alerts.</p></div>
      <section className="surface-card settings-page-card alert-settings-card">
        {error && <AlertMessage message={error} />}
        {loading ? <p role="status">Loading alert settings…</p> : SETTINGS.map(([key, title, description, Icon]) => (
          <div className="preference-row" key={key}>
            <span className="feature-icon feature-icon-teal"><Icon aria-hidden="true" /></span>
            <span className="preference-copy"><strong>{title}</strong><small>{description}</small></span>
            <div className="form-check form-switch">
              <input className="form-check-input" type="checkbox" role="switch" checked={settings[key]} onChange={(event) => { setSaved(false); setSettings((current) => ({ ...current, [key]: event.target.checked })); }} aria-label={title} />
            </div>
          </div>
        ))}
        <div className="settings-privacy-note"><FiShield /><span><strong>Your contact details stay private</strong><small>Email and phone alerts use the email and phone number saved in your profile.</small></span></div>
        <button className="btn btn-primary mt-4" type="button" onClick={save} disabled={loading || saving}>{saving ? "Saving…" : "Save alert settings"}</button>
        {saved && <p className="small text-success mt-2 mb-0" role="status"><FiCheck className="me-1" />Alert settings saved.</p>}
      </section>
    </div>
  );
}
