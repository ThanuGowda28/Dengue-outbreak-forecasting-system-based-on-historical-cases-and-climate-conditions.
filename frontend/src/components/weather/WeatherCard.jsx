export default function WeatherCard({ title, value, unit = "", description, icon: Icon, tone = "teal" }) {
  return (
    <article className={`weather-dashboard-card weather-tone-${tone}`}>
      <div className="weather-dashboard-card-heading">
        <span>{title}</span>
        <span className="weather-dashboard-icon"><Icon aria-hidden="true" /></span>
      </div>
      <p className="weather-dashboard-value">
        {value}
        {unit && value !== "Unavailable" && <span>{unit}</span>}
      </p>
      <small>{description}</small>
    </article>
  );
}
