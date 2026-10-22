import { useCallback, useEffect, useState } from "react";
import { FiBell, FiRefreshCw } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import { Pagination } from "../components/DashboardComponents.jsx";
import AlertStatus from "../components/alerts/AlertStatus.jsx";
import { getAlertHistory, sendPredictionAlerts } from "../services/alertService.js";
import { retryDetectionAlerts } from "../services/detectionService.js";
import "../styles/alerts.css";

const EMPTY_PAGE = { items: [], pagination: { page: 1, total_pages: 0, total_items: 0 } };

export default function AlertHistory() {
  const [result, setResult] = useState(EMPTY_PAGE);
  const [filters, setFilters] = useState({ type: "", status: "", start_date: "", end_date: "" });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setResult(await getAlertHistory({
        page,
        per_page: 20,
        type: filters.type || undefined,
        status: filters.status || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined
      }));
    } catch (loadError) {
      setError(loadError.response?.data?.message || "Alert history could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => { load(); }, [load]);

  async function retry(predictionId) {
    setRetrying(predictionId);
    setNotice("");
    try {
      const response = await sendPredictionAlerts(predictionId);
      setNotice(response.message);
      await load();
    } catch (retryError) {
      setError(retryError.response?.data?.message || "The alert could not be retried.");
    } finally {
      setRetrying(null);
    }

    async function retryDetection(detectionId) {
      setRetrying(detectionId);
      setNotice("");
      try {
        const result = await retryDetectionAlerts(detectionId);
        setNotice(result.message);
        await load();
      } catch (retryError) {
        setError(retryError.response?.data?.message || "The alert could not be retried.");
      } finally {
        setRetrying(null);
      }
    }
  }

  function changeFilter(key, value) {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">NOTIFICATIONS</span><h2>Alert history</h2><p>Review email, SMS, and in-app alerts for your predictions and breeding-site analyses.</p></div>
      {error && <AlertMessage message={error} />}
      {notice && <AlertMessage message={notice} variant="success" />}
      <section className="surface-card alert-history-card">
        <div className="alert-toolbar">
          <div className="alert-filters">
            <label><span>Channel</span><select className="form-select" value={filters.type} onChange={(event) => changeFilter("type", event.target.value)}><option value="">All channels</option><option value="email">Email</option><option value="sms">SMS</option><option value="in_app">In-app</option></select></label>
            <label><span>Status</span><select className="form-select" value={filters.status} onChange={(event) => changeFilter("status", event.target.value)}><option value="">All statuses</option><option value="queued">Queued</option><option value="retrying">Retrying</option><option value="sent">Success</option><option value="failed">Failed</option></select></label>
            <label><span>From</span><input className="form-control" type="date" value={filters.start_date} onChange={(event) => changeFilter("start_date", event.target.value)} /></label>
            <label><span>To</span><input className="form-control" type="date" value={filters.end_date} onChange={(event) => changeFilter("end_date", event.target.value)} /></label>
          </div>
          <button type="button" className="btn btn-outline-primary btn-sm" onClick={load} disabled={loading}><FiRefreshCw className="me-1" />Refresh</button>
        </div>
        {loading ? <p role="status" className="text-secondary">Loading alerts…</p> : result.items.length ? (
          <div className="table-responsive">
            <table className="table align-middle alert-table">
              <thead><tr><th>Alert</th><th>Date</th><th>Status</th><th>Recipient</th><th>Message preview</th><th /></tr></thead>
              <tbody>{result.items.map((alert) => (
                <tr key={alert.id}>
                  <td className="text-capitalize">{alert.alert_type}</td>
                  <td>{new Date(alert.sent_at || alert.created_at).toLocaleString()}</td>
                  <td><AlertStatus status={alert.status} type={alert.alert_type} /></td>
                  <td>{alert.recipient}</td>
                  <td className="alert-preview">{alert.message_preview}</td>
                  <td>{alert.status === "failed" && alert.prediction_id && <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => retry(alert.prediction_id)} disabled={retrying === alert.prediction_id}>{retrying === alert.prediction_id ? "Retrying…" : "Retry"}</button>}{alert.status === "failed" && alert.mosquito_detection_id && <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => retryDetection(alert.mosquito_detection_id)} disabled={retrying === alert.mosquito_detection_id}>{retrying === alert.mosquito_detection_id ? "Retrying…" : "Retry"}</button>}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <div className="alert-empty"><FiBell /><strong>No alerts found</strong><span>High-risk prediction alerts will appear here.</span></div>}
        <Pagination page={result.pagination.page || 1} pageCount={result.pagination.total_pages || 0} onChange={setPage} />
      </section>
    </div>
  );
}
