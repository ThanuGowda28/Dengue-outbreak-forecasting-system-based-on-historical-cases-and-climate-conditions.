import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { FiBell, FiCheck, FiGlobe, FiMoon, FiShield } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";

export default function Settings() {
  const {
    preferences,
    changePreference,
    savePreferences,
    loadPreferences,
    settingsLoading,
    settingsError
  } = useOutletContext();
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  function editPreference(name, value) {
    changePreference(name, value);
    setSaved(false);
    setSaveError("");
  }

  async function save() {
    setSaveError("");
    setSaved(false);
    setSaving(true);
    try {
      await savePreferences(preferences);
      setSaved(true);
    } catch (error) {
      setSaveError(error.response?.data?.message || "Preferences could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">PREFERENCES</span><h2>Workspace settings</h2><p>Manage preferences saved to your account.</p></div>
      <section className="surface-card settings-page-card">
        {settingsLoading && <p role="status">Loading saved preferences…</p>}
        {settingsError && (
          <>
            <AlertMessage message={settingsError} />
            <button type="button" className="btn btn-outline-primary btn-sm mb-3" onClick={loadPreferences} disabled={settingsLoading}>Retry loading preferences</button>
          </>
        )}
        {saveError && <AlertMessage message={saveError} />}
        <PreferenceRow icon={FiBell} title="Community notifications" description="Preference for risk and weather notifications." checked={preferences.alerts} disabled={settingsLoading || Boolean(settingsError)} onChange={(checked) => editPreference("alerts", checked)} />
        <PreferenceRow icon={FiGlobe} title="Weekly project summary" description="Preference for receiving a weekly project summary." checked={preferences.weekly_summary} disabled={settingsLoading || Boolean(settingsError)} onChange={(checked) => editPreference("weekly_summary", checked)} />
        <PreferenceRow icon={FiMoon} title="Dark appearance" description="Use the dark workspace appearance." checked={preferences.dark_mode} disabled={settingsLoading || Boolean(settingsError)} onChange={(checked) => editPreference("dark_mode", checked)} />
        <div className="settings-privacy-note"><FiShield /><span><strong>Account preferences</strong><small>Preferences are saved to your account and loaded when you open the workspace.</small></span></div>
        <button type="button" className="btn btn-primary mt-4" onClick={save} disabled={settingsLoading || saving || Boolean(settingsError)}>{saving ? "Saving…" : "Save preferences"}</button>
        {saved && <p className="small text-success mt-2 mb-0" role="status"><FiCheck className="me-1" /> Preferences saved to your account.</p>}
      </section>
    </div>
  );
}

function PreferenceRow({ icon: Icon, title, description, checked, disabled, onChange }) {
  return (
    <div className="preference-row"><span className="feature-icon feature-icon-teal"><Icon /></span><span className="preference-copy"><strong>{title}</strong><small>{description}</small></span><div className="form-check form-switch"><input className="form-check-input" type="checkbox" role="switch" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} aria-label={title} /></div></div>
  );
}
