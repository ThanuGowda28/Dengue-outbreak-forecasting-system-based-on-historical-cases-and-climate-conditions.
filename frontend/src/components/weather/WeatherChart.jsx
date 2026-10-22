import {
  CategoryScale,
  Chart as ChartJS,
  BarElement,
  Filler,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Filler);

const RANGE_DAYS = { today: 1, "7d": 7, "30d": 30 };

function chartEntries({ range, current, history, forecast }) {
  // Today's chart combines the live observation with same-day forecast intervals.
  if (range === "today") {
    const today = current.weather_date;
    const forecastToday = forecast.filter((entry) => entry.weather_date === today);
    return [
      { ...current, label: "Now" },
      ...forecastToday.map((entry, index) => ({ ...entry, label: `Forecast ${index + 1}` }))
    ];
  }

  const end = new Date(`${current.weather_date}T00:00:00Z`);
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - RANGE_DAYS[range] + 1);
  const rows = history
    .filter((entry) => {
      if (!entry.weather_date) return false;
      const date = new Date(`${entry.weather_date}T00:00:00Z`);
      return date >= start && date <= end;
    })
    .sort((left, right) => left.weather_date.localeCompare(right.weather_date));

  if (!rows.some((entry) => entry.weather_date === current.weather_date)) {
    rows.push({ ...current, weather_date: current.weather_date });
  }
  return rows.map((entry) => ({ ...entry, label: entry.weather_date }));
}

export default function WeatherChart({ title, metric, unit, color, range, current, history, forecast, historyError }) {
  const entries = chartEntries({ range, current, history, forecast });
  const values = entries.map((entry) => Number.isFinite(entry[metric]) ? entry[metric] : null);

  return (
    <article className="weather-chart-card">
      <div className="weather-chart-heading">
        <div><h3>{title}</h3><span>{range === "today" ? "Today" : `Last ${RANGE_DAYS[range]} days`}</span></div>
      </div>
      {values.some((value) => value !== null) ? (
        <div className="weather-chart-plot">
          <Line
            data={{
              labels: entries.map((entry) => entry.label),
              datasets: [{
                label: `${title} (${unit})`,
                data: values,
                borderColor: color,
                backgroundColor: `${color}20`,
                pointBackgroundColor: "#fff",
                pointBorderColor: color,
                pointBorderWidth: 2,
                pointRadius: 3,
                tension: 0.35,
                borderWidth: 2.5,
                fill: true,
                spanGaps: false
              }]
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false },
                tooltip: {
                  backgroundColor: "#163b45",
                  padding: 10,
                  callbacks: { label: (item) => `${item.parsed.y} ${unit}` }
                }
              },
              scales: {
                x: { grid: { display: false }, border: { display: false }, ticks: { color: "#82949b", maxTicksLimit: 7 } },
                y: {
                  border: { display: false },
                  grid: { color: "#edf1f3" },
                  ticks: { color: "#82949b", maxTicksLimit: 5, callback: (value) => `${value} ${unit}` }
                }
              }
            }}
          />
        </div>
      ) : (
        <p className="weather-chart-empty" role="status">
          {historyError || "No observations are available for this period."}
        </p>
      )}
    </article>
  );
}
