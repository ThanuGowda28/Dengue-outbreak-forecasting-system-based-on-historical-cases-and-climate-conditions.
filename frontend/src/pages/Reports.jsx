import { useEffect, useMemo, useState } from "react";
import { FiActivity, FiCloud, FiDownload, FiDroplet, FiThermometer, FiWind } from "react-icons/fi";
import { ChartCard, DashboardCard, EmptyState } from "../components/DashboardComponents.jsx";
import AlertMessage from "../components/AlertMessage.jsx";
import { DengueLineChart } from "../components/TrendCharts.jsx";
import { getStatistics, getWeatherReport } from "../services/dashboardService.js";
import { getDistricts, normalizeWeatherError } from "../services/weatherService.js";
import { useAuth } from "../context/AuthContext.jsx";
import AdminReports from "./AdminReports.jsx";

const today = () => new Date().toISOString().slice(0, 10);
const defaultStart = () => new Date(Date.now() - 29 * 86400000).toISOString().slice(0, 10);

export default function Reports() {
  const { user } = useAuth();
  return user?.role?.toLowerCase() === "admin" ? <AdminReports /> : <WeatherReports />;
}

function WeatherReports() {
  const [districts, setDistricts] = useState([]);
  const [district, setDistrict] = useState("");
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(today);
  const [report, setReport] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getDistricts()
      .then((items) => {
        if (active) {
          setDistricts(items);
          setDistrict(items[0]?.name || "");
        }
      })
      .catch((loadError) => { if (active) setError(normalizeWeatherError(loadError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!district || !startDate || !endDate) return undefined;
    let active = true;
    setLoading(true);
    setError("");
    const filters = { district, start_date: startDate, end_date: endDate };
    Promise.allSettled([
      getWeatherReport({ ...filters, limit: 100 }),
      getStatistics(filters)
    ])
      .then(([reportResult, statisticsResult]) => {
        if (!active) return;
        if (reportResult.status === "fulfilled") setReport(reportResult.value);
        else setError(normalizeWeatherError(reportResult.reason));
        if (statisticsResult.status === "fulfilled") setStatistics(statisticsResult.value);
        else if (reportResult.status === "fulfilled") setError(normalizeWeatherError(statisticsResult.reason));
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [district, startDate, endDate]);

  const rows = useMemo(
    () => extractObservations(report?.reports || [])
      .filter((row) => (!district || row.district?.toLowerCase() === district.toLowerCase())
        && row.weather_date >= startDate
        && row.weather_date <= endDate),
    [report, district, startDate, endDate]
  );
  const monthlyTemperature = useMemo(() => averageByMonth(rows), [rows]);
  const temperature = rows;
  const humidity = rows;
  const rainfall = rows;
  const labels = (items) => items.map((row) => row.month || new Date(`${row.weather_date}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" }));
  const countAvailable = rows.length;

  function changeDistrict(event) {
    setDistrict(event.target.value);
  }

  return (
    <div className="dashboard-page">
      <div className="page-intro page-intro-actions"><div><span className="page-overline">WEATHER REPORTS</span><h2>Climate observations</h2><p>Review weather readings returned by the backend and external providers.</p></div><button type="button" className="btn btn-outline-primary" onClick={() => window.print()}><FiDownload className="me-2" />Print report</button></div>
      <section className="surface-card report-filters">
        <div className="report-filter-field"><label className="form-label" htmlFor="report-district">District</label><select id="report-district" className="form-select" value={district} onChange={changeDistrict}>{districts.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}</select></div>
        <div className="report-filter-field"><label className="form-label" htmlFor="report-start">Start date</label><input id="report-start" className="form-control" type="date" value={startDate} max={endDate} onChange={(event) => setStartDate(event.target.value)} /></div>
        <div className="report-filter-field"><label className="form-label" htmlFor="report-end">End date</label><input id="report-end" className="form-control" type="date" value={endDate} min={startDate} max={today()} onChange={(event) => setEndDate(event.target.value)} /></div>
      </section>
      {error && <AlertMessage message={error} />}
      {loading && <div className="weather-loading"><span className="spinner-border spinner-border-sm text-primary" role="status" />Loading weather reports…</div>}
      <section className="row g-3">
        <div className="col-6 col-xl-3"><DashboardCard label="Weather observations" value={countAvailable} change={`${statistics?.statistics?.total_weather_records ?? 0} stored API requests · ${district || "selected district"}`} icon={<FiCloud />} tone="blue" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Temperature" value={average(rows, "temperature") == null ? "—" : `${average(rows, "temperature")}°C`} change="Observed average" icon={<FiThermometer />} tone="coral" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Humidity" value={average(rows, "humidity") == null ? "—" : `${average(rows, "humidity")}%`} change="Observed average" icon={<FiDroplet />} tone="teal" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Rainfall" value={sum(rows, "rainfall") == null ? "—" : `${sum(rows, "rainfall")} mm`} change="Observed total" icon={<FiWind />} tone="amber" /></div>
      </section>
      <section className="row g-3">
        <div className="col-xl-6"><ChartCard title="Monthly weather" subtitle="Monthly average temperature from stored weather history">{monthlyTemperature.length ? <DengueLineChart labels={labels(monthlyTemperature)} data={monthlyTemperature.map((row) => row.temperature)} color="#1976d2" fill label="Temperature (°C)" /> : <EmptyState title="No monthly weather available" description="No provider-backed records exist for this district and period." />}</ChartCard></div>
        <div className="col-xl-6"><ChartCard title="Temperature trend" subtitle="Recorded observations">{temperature.length ? <DengueLineChart labels={labels(temperature)} data={temperature.map((row) => row.temperature)} color="#e53935" fill label="Temperature (°C)" /> : <EmptyState title="No temperature history" description="No observations were returned." />}</ChartCard></div>
        <div className="col-xl-6"><ChartCard title="Rainfall trend" subtitle="Recorded rainfall per observation">{rainfall.length ? <DengueLineChart labels={labels(rainfall)} data={rainfall.map((row) => row.rainfall)} color="#009688" fill label="Rainfall (mm)" /> : <EmptyState title="No rainfall history" description="No observations were returned." />}</ChartCard></div>
        <div className="col-xl-6"><ChartCard title="Humidity trend" subtitle="Recorded relative humidity">{humidity.length ? <DengueLineChart labels={labels(humidity)} data={humidity.map((row) => row.humidity)} color="#43a047" fill label="Humidity (%)" /> : <EmptyState title="No humidity history" description="No observations were returned." />}</ChartCard></div>
      </section>
      <p className="demo-disclaimer"><FiActivity /> Reports include stored/provider weather only. No fabricated dengue case series or model-accuracy values are shown.</p>
    </div>
  );
}

function numericValues(rows, key) {
  return rows.map((row) => Number(row[key])).filter(Number.isFinite);
}

function average(rows, key) {
  const values = numericValues(rows, key);
  return values.length ? Number((values.reduce((total, value) => total + value, 0) / values.length).toFixed(1)) : null;
}

function sum(rows, key) {
  const values = numericValues(rows, key);
  return values.length ? Number(values.reduce((total, value) => total + value, 0).toFixed(1)) : null;
}

function averageByMonth(rows) {
  const grouped = rows.reduce((groups, row) => {
    if (!row.weather_date || row.temperature == null) return groups;
    const month = row.weather_date.slice(0, 7);
    groups[month] ||= [];
    groups[month].push(Number(row.temperature));
    return groups;
  }, {});
  return Object.entries(grouped).sort(([first], [second]) => first.localeCompare(second)).map(([month, values]) => ({ month, temperature: Number((values.reduce((a, b) => a + b, 0) / values.length).toFixed(1)) }));
}

function extractObservations(records) {
  return records.flatMap((record) => {
    const weather = record.weather || {};
    const entries = Array.isArray(weather.items)
      ? weather.items
      : weather.current
        ? [weather.current]
        : [];
    return entries
      .filter((entry) => entry.weather_date)
      .map((entry) => ({
        ...entry,
        district: record.location?.district || record.location?.city || "",
        source: record.source
      }));
  });
}
