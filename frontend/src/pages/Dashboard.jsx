import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import {
  Activity,
  ArrowRight,
  BellRing,
  CalendarDays,
  Cloud,
  CloudRain,
  Droplets,
  MapPinned,
  Settings,
  Sparkles,
  Thermometer,
  UserRound,
} from "lucide-react";
import AlertMessage from "../components/AlertMessage.jsx";
import { getDashboard } from "../services/dashboardService.js";
import { getForecastHistory } from "../services/forecastingService.js";
import { getCurrentWeather, normalizeWeatherError } from "../services/weatherService.js";
import { useAuth } from "../context/AuthContext.jsx";
import "../styles/dashboard-hub.css";

const QUICK_LINKS = [
  {
    title: "AI Forecast",
    description: "Generate an AI-powered dengue risk forecast.",
    to: "/forecasting",
    icon: Sparkles,
    tone: "mint",
  },
  {
    title: "Weather",
    description: "Explore current conditions and the five-day outlook.",
    to: "/weather",
    icon: Cloud,
    tone: "sky",
  },
  {
    title: "Risk Map",
    description: "View district-level dengue risk across the region.",
    to: "/risk-map",
    icon: MapPinned,
    tone: "aqua",
  },
  {
    title: "Forecast History",
    description: "Browse saved forecasts and recent activity.",
    to: "/history",
    icon: CalendarDays,
    tone: "amber",
  },
  {
    title: "Alerts",
    description: "Review notifications and manage alert preferences.",
    to: "/alerts",
    icon: BellRing,
    tone: "coral",
  },
  {
    title: "Profile",
    description: "Keep your account and location details up to date.",
    to: "/profile",
    icon: UserRound,
    tone: "blue",
  },
  {
    title: "Settings",
    description: "Personalize your dashboard and preferences.",
    to: "/settings",
    icon: Settings,
    tone: "slate",
  },
];

function greetingFor(hour) {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function formatTime(value) {
  if (!value) return "Waiting for an update";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Updated recently"
    : date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function formatDate(value) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function CountUp({ value, suffix = "" }) {
  const numericValue = Number(value);
  const motionValue = useMotionValue(0);
  const display = useTransform(motionValue, (current) => (
    `${Math.round(current * 10) / 10}${suffix}`
  ));

  useEffect(() => {
    if (!Number.isFinite(numericValue)) return undefined;
    const controls = animate(motionValue, numericValue, { duration: 0.75, ease: "easeOut" });
    return () => controls.stop();
  }, [motionValue, numericValue]);

  if (!Number.isFinite(numericValue)) return <span>—</span>;
  return <motion.span>{display}</motion.span>;
}

function makeNotifications(dashboard, latestForecast) {
  const alerts = (dashboard?.alerts || []).map((item) => ({
    id: `alert-${item.id || item.title}`,
    title: item.title || "New health alert",
    description: item.message || "Review your latest health notification.",
    createdAt: item.created_at,
    icon: BellRing,
    tone: "coral",
  }));
  const weatherUpdates = (dashboard?.recent_weather || []).flatMap((record) => {
    if (!["current", "forecast"].includes(record.record_type)) return [];
    const isForecast = record.record_type === "forecast";
    return [{
      id: `weather-${record.id}`,
      title: isForecast ? "Forecast generated" : "Weather updated",
      description: `${record.location?.district || record.location?.city || "Your location"} weather data is ready.`,
      createdAt: record.created_at || record.observed_at,
      icon: isForecast ? CloudRain : Cloud,
      tone: "sky",
    }];
  });
  const latestAssessment = dashboard?.latest_prediction;
  const assessments = latestAssessment ? [{
    id: `assessment-${latestAssessment.id}`,
    title: "Climate risk assessment complete",
    description: `${latestAssessment.risk_level || latestAssessment.risk || "Latest"} risk assessment for ${latestAssessment.state || latestAssessment.district || "your location"}.`,
    createdAt: latestAssessment.prediction_time || latestAssessment.date,
    icon: Sparkles,
    tone: "mint",
  }] : [];
  const forecasts = latestForecast ? [{
    id: `forecast-${latestForecast.id}`,
    title: "AI forecast ready",
    description: `${latestForecast.risk || "Latest"} case-trend forecast for ${latestForecast.state || "your location"}.`,
    createdAt: latestForecast.generated_at,
    icon: Sparkles,
    tone: "mint",
  }] : [];

  return [...alerts, ...weatherUpdates, ...assessments, ...forecasts]
    .sort((first, second) => new Date(second.createdAt || 0) - new Date(first.createdAt || 0))
    .slice(0, 3);
}

function WeatherSummary({ weather }) {
  const summary = [
    { label: "Temperature", value: weather?.temperature, suffix: "°C", icon: Thermometer, tone: "mint" },
    { label: "Humidity", value: weather?.humidity, suffix: "%", icon: Droplets, tone: "sky" },
    { label: "Rainfall", value: weather?.rainfall, suffix: " mm", icon: CloudRain, tone: "aqua" },
  ];

  return (
    <>
      {summary.map(({ label, value, suffix, icon: Icon, tone }, index) => (
        <motion.article
          className="hub-metric-card"
          key={label}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 + index * 0.07, duration: 0.35 }}
          whileHover={{ y: -4, scale: 1.015 }}
        >
          <span className={`hub-metric-icon tone-${tone}`}><Icon size={19} aria-hidden="true" /></span>
          <span className="hub-metric-value">
            {value == null ? "—" : <CountUp value={value} suffix={suffix} />}
          </span>
          <span className="hub-metric-label">{label}</span>
        </motion.article>
      ))}
    </>
  );
}

function SkeletonCard() {
  return (
    <div className="hub-skeleton-card" aria-hidden="true">
      <span />
      <span />
      <span />
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [latestForecast, setLatestForecast] = useState(null);
  const [weather, setWeather] = useState(null);
  const [weatherLocation, setWeatherLocation] = useState(null);
  const [weatherUpdatedAt, setWeatherUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [weatherError, setWeatherError] = useState("");
  const [dashboardError, setDashboardError] = useState("");
  const [forecastError, setForecastError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      setLoading(true);
      setWeatherError("");
      setDashboardError("");
      const [dashboardResult, weatherResult, forecastResult] = await Promise.allSettled([
        getDashboard(),
        user?.district
          ? getCurrentWeather({ district: user.district, state: user.state || "Karnataka" })
          : Promise.resolve(null),
        getForecastHistory({ page: 1, per_page: 1 }),
      ]);

      if (!active) return;
      if (dashboardResult.status === "fulfilled") {
        setDashboard(dashboardResult.value);
      } else {
        setDashboardError("Your dashboard summary could not be loaded. Please refresh to try again.");
      }
      if (forecastResult.status === "fulfilled") {
        setLatestForecast(forecastResult.value.items?.[0] || null);
      } else {
        setForecastError("Your latest forecast could not be loaded. Please try again later.");
      }

      const liveWeather = weatherResult.status === "fulfilled" ? weatherResult.value : null;
      const storedWeather = dashboardResult.status === "fulfilled"
        ? dashboardResult.value.weather
        : null;
      const current = liveWeather?.current?.temperature != null
        ? liveWeather.current
        : storedWeather?.current;
      setWeather(current?.temperature == null ? null : current);
      setWeatherLocation(liveWeather?.location || storedWeather?.location || null);
      setWeatherUpdatedAt(liveWeather?.last_updated || current?.weather_date || null);
      if (current?.temperature == null && weatherResult.status === "rejected") {
        setWeatherError(normalizeWeatherError(weatherResult.reason));
      }
      setLoading(false);
    }

    loadDashboard();
    return () => {
      active = false;
    };
  }, [user?.district, user?.state]);

  const greeting = greetingFor(new Date().getHours());
  const firstName = user?.full_name?.trim().split(/\s+/)[0] || "there";
  const today = new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date());
  const locationLabel = [weatherLocation?.district || weatherLocation?.city || user?.district, weatherLocation?.state || user?.state]
    .filter(Boolean)
    .join(", ") || "Location not set";
  const latestAssessment = dashboard?.latest_prediction;
  const riskValue = dashboard?.today_risk || latestAssessment?.risk_level || latestAssessment?.risk;
  const notifications = useMemo(() => makeNotifications(dashboard, latestForecast), [dashboard, latestForecast]);
  const lastUpdated = formatTime(weatherUpdatedAt);

  return (
    <main className="dashboard-page dashboard-hub">
      <motion.section
        className="hub-hero"
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
      >
        <div className="hub-hero-orb hub-hero-orb-one" aria-hidden="true" />
        <div className="hub-hero-orb hub-hero-orb-two" aria-hidden="true" />
        <div className="hub-hero-content">
          <div className="hub-hero-date"><CalendarDays size={15} aria-hidden="true" />{today}</div>
          <p className="hub-hero-greeting">{greeting}, {firstName}</p>
          <h2>Health Intelligence Platform</h2>
          <p className="hub-hero-location"><MapPinned size={16} aria-hidden="true" />{locationLabel}</p>
          <span className="hub-weather-label">CURRENT WEATHER</span>
          <div className="hub-hero-weather">
            <Cloud size={21} aria-hidden="true" />
            {loading
              ? "Checking local weather…"
              : weather
                ? `${weather.description || "Current conditions"} · ${weather.temperature}°C${weather.wind_speed == null ? "" : ` · Wind ${weather.wind_speed} m/s`}`
                : weatherError || "Weather conditions are not available right now."}
          </div>
          <div className="hub-hero-actions">
                    <Link className="hub-button hub-button-primary" to="/forecasting">
              <Sparkles size={18} aria-hidden="true" />Forecast Now
            </Link>
            <Link className="hub-button hub-button-glass" to="/risk-map">
              <MapPinned size={17} aria-hidden="true" />View risk map
            </Link>
          </div>
        </div>
        <div className="hub-hero-aside">
          <div className="hub-update-time">
            <span>WEATHER LAST UPDATED</span>
            <strong>{loading ? "Updating…" : lastUpdated}</strong>
          </div>
          <div className="hub-weather-art" aria-hidden="true">
            <div className="hub-weather-ring hub-weather-ring-outer" />
            <div className="hub-weather-ring hub-weather-ring-inner" />
            <Cloud className="hub-weather-cloud" size={76} strokeWidth={1.15} />
            <span className="hub-weather-spark hub-weather-spark-one" />
            <span className="hub-weather-spark hub-weather-spark-two" />
          </div>
        </div>
      </motion.section>

      {(dashboardError || (weatherError && !weather)) && (
        <AlertMessage message={dashboardError || weatherError} />
      )}
      {forecastError && <AlertMessage message={forecastError} />}

      <section className="hub-section" aria-label="Current health summary">
        <div className="hub-section-heading">
          <div><span className="hub-overline">TODAY’S SNAPSHOT</span><h3>Quick summary</h3></div>
          {loading && <span className="hub-loading-note"><span className="hub-spinner" />Refreshing</span>}
        </div>
        <div className="hub-metrics-grid">
          {loading
            ? [0, 1, 2, 3].map((item) => <SkeletonCard key={item} />)
            : <>
              <WeatherSummary weather={weather} />
              <motion.article
                className="hub-metric-card"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.33, duration: 0.35 }}
                whileHover={{ y: -4, scale: 1.015 }}
              >
                <span className="hub-metric-icon tone-coral"><Activity size={19} aria-hidden="true" /></span>
                <span className={`hub-risk-value risk-${String(riskValue || "").toLowerCase().replace(/\s+/g, "-")}`}>
                  {riskValue || "Not assessed"}
                </span>
                <span className="hub-metric-label">Current risk</span>
              </motion.article>
            </>}
        </div>
      </section>

      <section className="hub-section" aria-label="Quick access">
        <div className="hub-section-heading">
          <div><span className="hub-overline">YOUR WORKSPACE</span><h3>Quick access</h3></div>
          <span className="hub-section-caption">Everything you need, one click away</span>
        </div>
        <div className="hub-access-grid">
          {QUICK_LINKS.map(({ title, description, to, icon: Icon, tone }, index) => (
            <motion.div
              key={to}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(index * 0.045, 0.28), duration: 0.35 }}
              whileHover={{ y: -5 }}
              whileTap={{ scale: 0.98 }}
            >
              <Link className="hub-access-card" to={to}>
                <span className={`hub-access-icon tone-${tone}`}><Icon size={21} strokeWidth={1.8} aria-hidden="true" /></span>
                <span className="hub-access-copy"><strong>{title}</strong><small>{description}</small></span>
                <ArrowRight className="hub-access-arrow" size={17} aria-hidden="true" />
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="hub-lower-grid">
        <article className="hub-panel hub-forecast-panel">
          <div className="hub-panel-heading">
            <div><span className="hub-overline">AI FORECAST</span><h3>Latest Forecast</h3></div>
            <span className="hub-panel-symbol tone-mint"><Sparkles size={18} aria-hidden="true" /></span>
          </div>
          {latestForecast ? (
            <div className="hub-latest-result">
              <span className={`hub-risk-pill risk-${String(latestForecast.risk || "").toLowerCase().replace(/\s+/g, "-")}`}>
                {latestForecast.risk || "Forecast complete"}
              </span>
              <strong>{latestForecast.district || latestForecast.state || "Location not available"}</strong>
              <span>{formatDate(latestForecast.generated_at)} · {latestForecast.forecast_year}</span>
              <Link to="/history">View details <ArrowRight size={15} aria-hidden="true" /></Link>
            </div>
          ) : (
            <div className="hub-empty-state">
              <span className="hub-empty-icon"><Sparkles size={20} aria-hidden="true" /></span>
              <div><strong>No forecast yet</strong><p>Your latest saved dengue risk forecast will appear here.</p></div>
              <Link to="/forecasting" aria-label="Create a forecast"><ArrowRight size={17} /></Link>
            </div>
          )}
        </article>

        <article className="hub-panel">
          <div className="hub-panel-heading">
            <div><span className="hub-overline">LATEST UPDATES</span><h3>Recent notifications</h3></div>
            <Link className="hub-view-all" to="/alerts">View all <ArrowRight size={14} aria-hidden="true" /></Link>
          </div>
          {loading ? (
            <div className="hub-notification-skeletons" aria-label="Loading notifications">
              <span /><span /><span />
            </div>
          ) : notifications.length ? (
            <div className="hub-notification-list">
              {notifications.map(({ id, title, description, createdAt, icon: Icon, tone }) => (
                <div className="hub-notification" key={id}>
                  <span className={`hub-notification-icon tone-${tone}`}><Icon size={16} aria-hidden="true" /></span>
                  <span className="hub-notification-copy"><strong>{title}</strong><small>{description}</small></span>
                  <time>{formatTime(createdAt)}</time>
                </div>
              ))}
            </div>
          ) : (
            <div className="hub-empty-notifications">
              <BellRing size={19} aria-hidden="true" />
              <span>You’re all caught up. New updates will appear here.</span>
            </div>
          )}
        </article>
      </section>

    </main>
  );
}
