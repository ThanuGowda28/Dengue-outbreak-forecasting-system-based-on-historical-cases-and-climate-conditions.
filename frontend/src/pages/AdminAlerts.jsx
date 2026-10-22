import { useCallback, useEffect, useState } from "react";
import { FiDownload, FiRefreshCw } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import { Pagination } from "../components/DashboardComponents.jsx";
import AlertStatus from "../components/alerts/AlertStatus.jsx";
import { getAdminAlertHistory, exportAdminAlerts } from "../services/alertService.js";
import "../styles/alerts.css";

export default function AdminAlerts() {
  const [result, setResult] = useState({ items: [], pagination: { page: 1, total_pages: 0, total_items: 0 } });
  const [filters, setFilters] = useState({ search: "", type: "", status: "", start_date: "", end_date: "" });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  const params = {
    page,
    per_page: 50,
    search: filters.search || undefined,
    type: filters.type || undefined,
    status: filters.status || undefined,
    start_date: filters.start_date || undefined,
    end_date: filters.end_date || undefined
  };
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setResult(await getAdminAlertHistory(params));
    } catch (loadError) {
      setError(loadError.response?.data?.message || "Alert records could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => { load(); }, [load]);

  function changeFilter(key, value) {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  }

  async function exportCsv() {
    setExporting(true);
    setError("");
    try {
      const blob = await exportAdminAlerts({
        search: filters.search || undefined,
        type: filters.type || undefined,
        status: filters.status || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "dengue-alert-history.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (exportError) {
      setError(exportError.response?.data?.message || "Alert history could not be exported.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">ADMINISTRATION</span><h2>Alert management</h2><p>Search delivery history, filter outcomes, and export the matching records.</p></div>
      {error && <AlertMessage message={error} />}
      <section className="surface-card alert-history-card">
        <div className="alert-admin-toolbar">
          <input className="form-control" aria-label="Search alerts" placeholder="Search recipient, user, or message" value={filters.search} onChange={(event) => changeFilter("search", event.target.value)} />
          <select className="form-select" aria-label="Filter alert type" value={filters.type} onChange={(event) => changeFilter("type", event.target.value)}><option value="">All channels</option><option value="email">Email</option><option value="sms">SMS</option><option value="in_app">In-app</option></select>
          <select className="form-select" aria-label="Filter alert status" value={filters.status} onChange={(event) => changeFilter("status", event.target.value)}><option value="">All outcomes</option><option value="sent">Success</option><option value="failed">Failed</option><option value="queued">Queued</option><option value="retrying">Retrying</option></select>
          <input className="form-control" aria-label="From date" type="date" value={filters.start_date} onChange={(event) => changeFilter("start_date", event.target.value)} />
          <input className="form-control" aria-label="To date" type="date" value={filters.end_date} onChange={(event) => changeFilter("end_date", event.target.value)} />
          <button type="button" className="btn btn-outline-primary btn-sm" onClick={load} disabled={loading}><FiRefreshCw /></button>
          <button type="button" className="btn btn-primary btn-sm" onClick={exportCsv} disabled={exporting}><FiDownload className="me-1" />{exporting ? "Exporting…" : "Export CSV"}</button>
        </div>
        {loading ? <p role="status" className="text-secondary">Loading alert history…</p> : result.items.length ? (
          <div className="table-responsive">
            <table className="table align-middle alert-table">
              <thead><tr><th>User</th><th>Channel</th><th>Date</th><th>Status</th><th>Recipient</th><th>Message preview</th><th>Attempts</th></tr></thead>
              <tbody>{result.items.map((alert) => (
                <tr key={alert.id}>
                  <td>{alert.user_name}<small className="d-block text-secondary">{alert.user_email}</small></td>
                  <td className="text-capitalize">{alert.alert_type}</td>
                  <td>{new Date(alert.sent_at || alert.created_at).toLocaleString()}</td>
                  <td><AlertStatus status={alert.status} type={alert.alert_type} /></td>
                  <td>{alert.recipient}</td>
                  <td className="alert-preview">{alert.message_preview}</td>
                  <td>{alert.attempts}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <p className="text-secondary">No alert records match the selected filters.</p>}
        <Pagination page={result.pagination.page || 1} pageCount={result.pagination.total_pages || 0} onChange={setPage} />
      </section>
    </div>
  );
}
