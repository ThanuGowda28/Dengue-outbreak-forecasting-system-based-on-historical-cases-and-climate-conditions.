import { useEffect, useState } from "react";
import { FiDatabase, FiTarget, FiUsers, FiCloud } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import { ChartCard, DashboardCard, EmptyState } from "../components/DashboardComponents.jsx";
import { DengueLineChart } from "../components/TrendCharts.jsx";
import { getAdminReports } from "../services/adminService.js";

const today = () => new Date().toISOString().slice(0, 10);
const defaultStart = () => new Date(Date.now() - 29 * 86400000).toISOString().slice(0, 10);

export default function AdminReports() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(today);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    getAdminReports({ start_date: startDate, end_date: endDate })
      .then((result) => { if (active) setReport(result); })
      .catch((requestError) => { if (active) setError(requestError.response?.data?.message || "Administrator report could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [startDate, endDate]);

  const summary = report?.summary || {};
  const months = report?.monthly_predictions || [];
  const risks = report?.predictions_by_risk || {};
  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">ADMINISTRATOR REPORTS</span><h2>System activity</h2><p>Totals across registered accounts, saved risk assessments, and weather requests.</p></div>
      <section className="surface-card report-filters" aria-label="Administrator report date range">
        <div className="report-filter-field"><label className="form-label" htmlFor="admin-report-start">Start date</label><input id="admin-report-start" className="form-control" type="date" value={startDate} max={endDate} onChange={(event) => setStartDate(event.target.value)} /></div>
        <div className="report-filter-field"><label className="form-label" htmlFor="admin-report-end">End date</label><input id="admin-report-end" className="form-control" type="date" value={endDate} min={startDate} max={today()} onChange={(event) => setEndDate(event.target.value)} /></div>
      </section>
      {error && <AlertMessage message={error} />}
      {loading && <p role="status">Loading administrator reports…</p>}
      <section className="row g-3">
        <div className="col-6 col-xl-3"><DashboardCard label="Registered users" value={summary.registered_users ?? "—"} icon={<FiUsers />} tone="teal" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Risk assessments" value={summary.predictions ?? "—"} icon={<FiTarget />} tone="amber" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Weather records" value={summary.weather_records ?? "—"} icon={<FiCloud />} tone="blue" /></div>
        <div className="col-6 col-xl-3"><DashboardCard label="Weather categories" value={Object.keys(report?.weather_records_by_type || {}).length} icon={<FiDatabase />} tone="coral" /></div>
      </section>
      <section className="row g-3">
        <div className="col-xl-7"><ChartCard title="Monthly risk assessments" subtitle="Saved assessments by calendar month">{months.length ? <DengueLineChart labels={months.map((item) => item.month)} data={months.map((item) => item.count)} color="#1976d2" fill label="Assessments" /> : <EmptyState title="No assessment history" description="There are no saved risk assessments to report." />}</ChartCard></div>
        <div className="col-xl-5"><ChartCard title="Risk distribution" subtitle="Saved climate risk assessments">{Object.keys(risks).length ? <DengueLineChart labels={Object.keys(risks)} data={Object.values(risks)} color="#e53935" fill label="Assessments" /> : <EmptyState title="No risk results" description="Risk totals will appear after assessments are saved." />}</ChartCard></div>
      </section>
      <p className="demo-disclaimer">Reports contain stored records only. They do not assert disease prevalence, model accuracy, or clinical outcomes.</p>
    </div>
  );
}
