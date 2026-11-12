import { useState } from "react";
import {
  FiClock,
  FiCloud,
  FiDroplet,
  FiSun,
  FiThermometer,
  FiWind
} from "react-icons/fi";
import RecommendationCard from "./RecommendationCard.jsx";
import WeatherAlert from "./WeatherAlert.jsx";
import WeatherCard from "./WeatherCard.jsx";
import WeatherChart from "./WeatherChart.jsx";

const chartRanges = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" }
];

function displayValue(value, digits = 1) {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : "Unavailable";
}

function updatedLabel(value) {
  if (!value) return "Unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Unavailable"
    : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export default function WeatherDashboardPanel({ current, history, forecast, lastUpdated, historyError }) {
  const [range, setRange] = useState("7d");
  const metrics = [
    { title: "Temperature", value: displayValue(current.temperature), unit: "°C", description: "Current air temperature", icon: FiThermometer, tone: "coral" },
    { title: "Humidity", value: displayValue(current.humidity, 0), unit: "%", description: "Relative humidity", icon: FiDroplet, tone: "blue" },
    { title: "Rainfall", value: displayValue(current.rainfall), unit: "mm", description: "Recent reported rainfall", icon: FiCloud, tone: "teal" },
    { title: "Wind speed", value: displayValue(current.wind_speed), unit: "m/s", description: "Near-surface wind", icon: FiWind, tone: "violet" },
    { title: "Weather condition", value: current.description || "Unavailable", description: "Provider-reported conditions", icon: FiCloud, tone: "blue" },
    { title: "UV index", value: displayValue(current.uv_index), description: "Not available for this location", icon: FiSun, tone: "amber" },
    { title: "Last updated", value: updatedLabel(lastUpdated), description: "Provider observation time", icon: FiClock, tone: "teal" }
  ];
  const charts = [
    { title: "Temperature trend", metric: "temperature", unit: "°C", color: "#e8785d" },
    { title: "Humidity trend", metric: "humidity", unit: "%", color: "#478ad0" },
    { title: "Rainfall trend", metric: "rainfall", unit: "mm", color: "#15988d" },
    { title: "Wind speed trend", metric: "wind_speed", unit: "m/s", color: "#8566bc" }
  ];
  const explanation = [
    Number.isFinite(current.humidity) && current.humidity > 80 ? "Humidity exceeds 80%." : null,
    Number.isFinite(current.rainfall) && current.rainfall > 100 ? "Reported rainfall exceeds 100 mm." : null,
    Number.isFinite(current.temperature) && current.temperature >= 25 && current.temperature <= 30
      ? "Temperature is within a range associated with mosquito breeding."
      : null
  ].filter(Boolean);

  return (
    <div className="weather-dashboard">
      <WeatherAlert current={current} />
      <section className="weather-metric-grid" aria-label="Live weather conditions">
        {metrics.map((metric) => <WeatherCard key={metric.title} {...metric} />)}
      </section>

      {/* The saved ensemble expects annual inputs, so live values are not passed as proxies. */}
      <section className="weather-risk-card" aria-labelledby="weather-risk-title">
        <div className="weather-risk-heading">
          <div><span className="page-overline">ENSEMBLE MODEL</span><h2 id="weather-risk-title">Current dengue risk</h2></div>
          <span className="weather-risk-unavailable">Unavailable</span>
        </div>
        <p>
          A scientifically valid ensemble estimate cannot be produced from a live weather snapshot.
          The trained model requires annual climate aggregates, including annual rainfall and solar
          radiation; current readings are not substituted for those inputs.
        </p>
        <p className="weather-risk-explanation">
          {explanation.length ? `Weather conditions to watch: ${explanation.join(" ")}` : "No configured weather alert thresholds are currently exceeded."}
          {" "}These indicators are not a dengue outbreak forecast.
        </p>
      </section>

      <section className="weather-trends" aria-labelledby="weather-trends-title">
        <div className="weather-section-heading weather-trends-heading">
          <div><h2 id="weather-trends-title">Weather trends</h2><p>Provider observations for the selected period.</p></div>
          <div className="weather-range-selector" role="group" aria-label="Weather chart date range">
            {chartRanges.map((item) => (
              <button
                key={item.value}
                type="button"
                className={range === item.value ? "active" : ""}
                aria-pressed={range === item.value}
                onClick={() => setRange(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <div className="weather-chart-grid">
          {charts.map((chart) => (
            <WeatherChart
              key={chart.metric}
              {...chart}
              range={range}
              current={current}
              history={history}
              forecast={forecast}
              historyError={historyError}
            />
          ))}
        </div>
      </section>

      <RecommendationCard />
    </div>
  );
}
