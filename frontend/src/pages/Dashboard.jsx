import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FiActivity,
  FiAlertTriangle,
  FiArrowUpRight,
  FiCloud,
  FiDownload,
  FiMap,
  FiPlus,
  FiTarget
} from "react-icons/fi";
import { ChartCard, DashboardCard, EmptyState, PredictionCard, WeatherCard } from "../components/DashboardComponents.jsx";
import AlertMessage from "../components/AlertMessage.jsx";
import { DengueLineChart } from "../components/TrendCharts.jsx";
import { getDashboard, getStatistics } from "../services/dashboardService.js";
import { getCurrentWeather, normalizeWeatherError } from "../services/weatherService.js";
import { useAuth } from "../context/AuthContext.jsx";

const chartRows = (items = [], key) => Array.isArray(items)
  ? items.filter((item) => item?.[key] != null && item?.weather_date).sort((a, b) => new Date(a.weather_date) - new Date(b.weather_date))
  : [];

export default function Dashboard() {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [weather, setWeather] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      const [dashboardResult, weatherResult, statisticsResult] = await Promise.allSettled([
        getDashboard(),
        user?.district ? getCurrentWeather({ district: user.district, state: user.state || "Karnataka" }) : Promise.resolve(null),
        getStatistics()
      ]);
      if (!active) return;
      if (dashboardResult.status === "fulfilled") setDashboard(dashboardResult.value);
      else setError(normalizeWeatherError(dashboardResult.reason));
      if (weatherResult.status === "fulfilled" && weatherResult.value) {
        const current = weatherResult.value.current;
        setWeather(current?.temperature == null ? null : current);
      } else if (dashboardResult.status === "fulfilled") {
        const current = dashboardResult.value.weather?.current;
        setWeather(current?.temperature == null ? null : current);
      }
      if (weatherResult.status === "rejected" && dashboardResult.status === "fulfilled" && dashboardResult.value.weather?.current?.temperature == null) {
        setError(normalizeWeatherError(weatherResult.reason));
      }
      if (statisticsResult.status === "fulfilled") setStatistics(statisticsResult.value);
      setLoading(false);
    }
    load();
    return () => { active = false; };
  }, [user?.district, user?.state]);

  const recentPredictions = dashboard?.recent_predictions || [];
  const alerts = dashboard?.alerts || [];
  const reportStatistics = statistics?.statistics || {};
  const monthlyRows = (reportStatistics.monthly_weather || []).filter((item) => item.temperature != null);
  const temperatureRows = chartRows(reportStatistics.temperature_trend, "temperature");
  const latestPrediction = dashboard?.latest_prediction;
  const riskDistribution = dashboard?.risk_distribution || {};
  const riskAvailable = Boolean(dashboard?.risk_summary?.available);
  const WeatherIcon = FiCloud;
  const quickActions = [
    { title: "Predict now", description: "Enter a district and climate readings.", icon: FiPlus, to: "/prediction", color: "teal" },
    { title: "View district map", description: "Load current weather and climate history.", icon: FiMap, to: "/risk-map", color: "blue" },
    { title: "Health information", description: "Review symptoms and prevention guidance.", icon: FiAlertTriangle, to: "/symptoms", color: "coral" },
    { title: "Weather reports", description: "Explore provider-backed climate history.", icon: FiDownload, to: "/reports", color: "violet" }
  ];

  return (
    <div className="dashboard-page">
      <div className="welcome-strip">
        <div><span className="page-overline">{new Intl.DateTimeFormat(undefined, { dateStyle: "full" }).format(new Date()).toUpperCase()}</span><h2>Welcome back, stay informed.</h2><p>Current weather and your saved public-health records, when available.</p></div>
        <Link className="btn btn-light btn-sm" to="/prediction"><FiTarget className="me-2" />Climate inputs</Link>
      </div>
      {error && <AlertMessage message={error} />}
      {loading && <div className="weather-loading"><span className="spinner-border spinner-border-sm text-primary" role="status" />Loading your live dashboard…</div>}
      <section className="row g-3" aria-label="Current dashboard data">
        <div className="col-6 col-xl-3"><DashboardCard label="Current weather" value={weather?.temperature == null ? "Unavailable" : `${weather.temperature}°C`} change={weather?.description || user?.district || "Weather not available"} icon={<WeatherIcon />} tone="blue" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Latest prediction" value={latestPrediction?.risk_level || "None"} change={latestPrediction?.state || "No saved result"} icon={<FiTarget />} tone="teal" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Today's risk" value={dashboard?.today_risk || "Not assessed"} change={riskAvailable ? "Latest saved assessment today" : "No assessment today"} icon={<FiActivity />} tone="amber" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Prediction count" value={dashboard?.prediction_count ?? recentPredictions.length} change="Saved records" icon={<FiTarget />} tone="teal" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Active alerts" value={alerts.length} change="Server-provided notices" icon={<FiAlertTriangle />} tone="coral" /></div>
      </section>
      <section className="row g-3">
        <div className="col-xl-8"><ChartCard title="Observed temperature trend" subtitle="Weather history recorded for your district">{temperatureRows.length ? <DengueLineChart labels={temperatureRows.map((row) => new Date(`${row.weather_date}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" }))} data={temperatureRows.map((row) => row.temperature)} fill label="Temperature (°C)" /> : <EmptyState title="No weather trend available" description="Load current weather or a history report to populate this chart." />}</ChartCard></div>
        <div className="col-xl-4"><div className="surface-card forecast-card"><div className="surface-heading"><div><h2>Current conditions</h2><p>{weather?.weather_date || "No current observation"}</p></div><Link to="/weather" aria-label="View weather details"><FiArrowUpRight /></Link></div>{weather ? <><div className="forecast-mini"><WeatherCard day={user?.district || "Selected district"} icon={WeatherIcon} high={Math.round(weather.temperature)} low="—" condition={weather.description || "Current conditions"} current /></div><div className="weather-mini-stats"><span><small>Humidity</small><strong>{weather.humidity ?? "—"}%</strong></span><span><small>Rainfall</small><strong>{weather.rainfall ?? "—"} mm</strong></span><span><small>Wind</small><strong>{weather.wind_speed ?? "—"} m/s</strong></span></div></> : <EmptyState title="Weather unavailable" description="Check your provider configuration or search a location on the weather page." action={<Link className="text-link small" to="/weather">Open weather <FiArrowUpRight /></Link>} />}</div></div>
      </section>
      <section className="row g-3">
        <div className="col-xl-7"><div className="surface-card"><div className="surface-heading"><div><h2>Recent predictions</h2><p>Saved results from the prediction service</p></div><Link className="text-link small" to="/history">View history <FiArrowUpRight /></Link></div>{recentPredictions.length ? <div className="prediction-list">{recentPredictions.slice(0, 4).map((prediction) => <PredictionCard key={prediction.id} {...prediction} />)}</div> : <EmptyState icon={FiTarget} title="No predictions recorded" description="Run an ensemble prediction to save a result here." />}</div></div>
        <div className="col-xl-5"><div className="surface-card risk-summary"><div className="surface-heading"><div><h2>Public-health alerts</h2><p>Notifications returned by the backend</p></div><FiAlertTriangle className="surface-heading-icon" /></div>{alerts.length ? <div className="activity-list">{alerts.map((alert) => <article key={alert.id || alert.title} className="activity-row"><span className="activity-icon"><FiAlertTriangle /></span><div><strong>{alert.title}</strong><p>{alert.message}</p><small>{alert.created_at}</small></div></article>)}</div> : <EmptyState title="No active alerts" description="The dashboard will show official server-provided alerts here when available." />}</div></div>
      </section>
      <section className="row g-3">
        <div className="col-xl-7"><ChartCard title="Monthly climate summary" subtitle="Monthly temperature averages from recorded weather data">{monthlyRows.length ? <DengueLineChart labels={monthlyRows.map((row) => row.month)} data={monthlyRows.map((row) => row.temperature)} color="#1976d2" fill label="Average temperature (°C)" /> : <EmptyState title="No monthly climate data" description="Monthly observations will appear as provider history is collected." />}</ChartCard></div>
        <div className="col-xl-5"><div className="surface-card risk-summary"><div className="surface-heading"><div><h2>Risk status</h2><p>Risk levels are not inferred from weather</p></div><FiMap className="surface-heading-icon" /></div>{Object.values(riskDistribution).some((count) => count > 0) ? <div className="dashboard-risk-distribution">{["Low Risk", "Moderate Risk", "High Risk"].map((risk) => { const total = Object.values(riskDistribution).reduce((sum, count) => sum + count, 0); const count = riskDistribution[risk] || 0; return <div className="risk-distribution-row" key={risk}><div><span>{risk}</span><strong>{count}</strong></div><div className="progress"><div className={`progress-bar bg-${risk.startsWith("High") ? "danger" : risk.startsWith("Moderate") ? "warning" : "success"}`} style={{ width: `${total ? count / total * 100 : 0}%` }} /></div></div>; })}<p className="small text-secondary mt-3">Saved model classifications only; not official surveillance.</p></div> : <EmptyState icon={FiActivity} title="No risk history" description="Risk distribution appears after model predictions are saved." action={<Link className="text-link small" to="/prediction">Run a prediction <FiArrowUpRight /></Link>} />}</div></div>
      </section>
      <section className="surface-card">
        <div className="surface-heading"><div><h2>Quick actions</h2><p>Weather and health information tools</p></div></div>
        <div className="row g-3">{quickActions.map(({ title, description, icon: Icon, to, color }) => <div className="col-sm-6 col-xl-3" key={title}><Link className="quick-action-card" to={to}><span className={`feature-icon feature-icon-${color}`}><Icon /></span><strong>{title}</strong><p>{description}</p><FiArrowUpRight className="quick-action-arrow" /></Link></div>)}</div>
      </section>
      <p className="demo-disclaimer">Weather is supplied by configured providers. Model classifications use annual climate inputs and are research outputs, not medical advice.</p>
    </div>
  );
}
