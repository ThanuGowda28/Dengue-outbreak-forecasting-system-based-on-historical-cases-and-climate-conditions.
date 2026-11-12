import { useEffect, useState } from "react";
import { FiArrowUpRight, FiDatabase, FiTarget, FiUsers } from "react-icons/fi";
import { Link } from "react-router-dom";
import { ChartCard, DashboardCard, EmptyState } from "../components/DashboardComponents.jsx";
import AlertMessage from "../components/AlertMessage.jsx";
import { DengueLineChart } from "../components/TrendCharts.jsx";
import { getAdminDashboard, getAdminReports } from "../services/adminService.js";

export default function AdminDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function load() {
      const errors = [];
      try {
        const result = await getAdminDashboard();
        if (!active) return;
        setDashboard(result);
      } catch (requestError) {
        errors.push(requestError.response?.data?.message || "Administrator summary could not be loaded.");
      }
      try {
        const result = await getAdminReports();
        if (!active) return;
        setStatistics(result);
      } catch (requestError) {
        errors.push(requestError.response?.data?.message || "Administrator report statistics could not be loaded.");
      }
      if (active) {
        setError(errors.join(" "));
        setLoading(false);
      }
    }
    load();
    return () => { active = false; };
  }, []);

  const reportStatistics = statistics || {};
  const metrics = dashboard?.metrics || {};
  const monthly = Array.isArray(reportStatistics.monthly_predictions) ? reportStatistics.monthly_predictions : [];
  const recentPredictions = dashboard?.recent_predictions || [];
  const recentUsers = dashboard?.recent_users || [];

  return (
    <div className="dashboard-page">
      <div className="welcome-strip admin-welcome"><div><span className="page-overline">PROJECT ADMINISTRATION</span><h2>Workspace overview</h2><p>View database-backed account and climate summaries.</p></div><Link className="btn btn-light btn-sm" to="/train-model"><FiTarget className="me-2" />Model workspace</Link></div>
      {error && <AlertMessage message={error} />}
      {loading && <div className="weather-loading"><span className="spinner-border spinner-border-sm text-primary" role="status" />Loading administrative summary…</div>}
      <section className="row g-3">
        <div className="col-6 col-xl-3"><DashboardCard label="Registered users" value={metrics.user_count ?? "—"} change="All accounts" icon={<FiUsers />} tone="teal" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Weather records" value={metrics.weather_record_count ?? "—"} change="Stored provider requests" icon={<FiDatabase />} tone="blue" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Risk assessments" value={metrics.prediction_count ?? "—"} change="Saved climate risk assessments" icon={<FiTarget />} tone="amber" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Administrators" value={metrics.administrator_count ?? "—"} change="Role-managed accounts" icon={<FiUsers />} tone="coral" /></div>
      </section>
      <section className="row g-3">
        <div className="col-xl-7"><ChartCard title="Monthly risk assessments" subtitle="Saved assessments grouped by month">{monthly.length ? <DengueLineChart labels={monthly.map((row) => row.month)} data={monthly.map((row) => row.count)} color="#1976d2" fill label="Assessments" /> : <EmptyState title="No assessment history" description="Monthly totals appear after climate risk assessments are saved." />}</ChartCard></div>
        <div className="col-xl-5"><ChartCard title="Risk distribution" subtitle="Saved climate risk assessments">{Object.keys(dashboard?.risk_distribution || {}).length ? <DengueLineChart labels={Object.keys(dashboard.risk_distribution)} data={Object.values(dashboard.risk_distribution)} color="#009688" fill label="Assessments" /> : <EmptyState title="No risk assessments" description="No saved climate risk assessments are available yet." />}</ChartCard></div>
      </section>
      <section className="row g-3">
        <div className="col-xl-6"><div className="surface-card"><div className="surface-heading"><div><h2>Recent risk assessments</h2><p>Results from the climate risk assessment model</p></div><Link className="text-link small" to="/admin/predictions">Manage assessments <FiArrowUpRight /></Link></div>{recentPredictions.length ? <div className="prediction-list">{recentPredictions.map((row) => <article className="activity-row" key={row.id}><span className="activity-icon"><FiTarget /></span><div><strong>{row.state}</strong><p>{row.risk_level}</p><small>{new Date(row.prediction_time).toLocaleString()}</small></div></article>)}</div> : <EmptyState icon={FiTarget} title="No assessment records" description="No saved climate risk assessments are available." />}</div></div>
        <div className="col-xl-6"><div className="surface-card"><div className="surface-heading"><div><h2>Recent accounts</h2><p>Recently created user records</p></div><Link className="text-link small" to="/users">Manage users <FiArrowUpRight /></Link></div>{recentUsers.length ? <div className="activity-list">{recentUsers.map((item) => <article className="activity-row" key={item.id}><span className="activity-icon"><FiUsers /></span><div><strong>{item.full_name}</strong><p>{item.email}</p><small>{item.role} · {new Date(item.created_at).toLocaleDateString()}</small></div></article>)}</div> : <EmptyState title="No registered accounts" description="No user records are available." />}</div></div>
      </section>
      <p className="demo-disclaimer">Counts reflect saved project records. No model accuracy or fabricated case estimates are presented.</p>
    </div>
  );
}
