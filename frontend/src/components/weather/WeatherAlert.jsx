import { FiAlertTriangle } from "react-icons/fi";

export default function WeatherAlert({ current }) {
  const triggers = [];
  if (Number.isFinite(current.rainfall) && current.rainfall > 100) triggers.push("rainfall exceeds 100 mm");
  if (Number.isFinite(current.humidity) && current.humidity > 80) triggers.push("humidity exceeds 80%");
  if (!triggers.length) return null;

  return (
    <aside className="weather-alert" role="alert">
      <FiAlertTriangle aria-hidden="true" />
      <div>
        <strong>High Risk Alert</strong>
        <p>Current weather alert: {triggers.join(" and ")}. This is a weather threshold alert, not a dengue case forecast.</p>
      </div>
    </aside>
  );
}
