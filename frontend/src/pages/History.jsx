import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Download,
  FileText,
  Search,
  Trash2,
} from "lucide-react";
import AlertMessage from "../components/AlertMessage.jsx";
import { EmptyState, Pagination, RiskIndicator } from "../components/DashboardComponents.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import { getAlertHistory } from "../services/alertService.js";
import { deleteDetection, getDetectionHistory } from "../services/detectionService.js";
import { getForecastHistory } from "../services/forecastingService.js";
import { deletePredictionHistory, getPredictionHistory } from "../services/predictionService.js";
import { csvCell, toTimelineItems } from "../utils/historyTimeline.js";

const PAGE_SIZE = 10;

async function getAllPages(fetchPage) {
  const first = await fetchPage(1);
  const items = [...(first.items || [])];
  const pageCount = first.pagination?.total_pages || 1;
  for (let page = 2; page <= pageCount; page += 1) {
    const result = await fetchPage(page);
    items.push(...(result.items || []));
  }
  return items;
}

export default function History() {
  const [records, setRecords] = useState([]);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [activity, setActivity] = useState("all");
  const [risk, setRisk] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError("");
    try {
      const [forecasts, assessments, alerts, detections] = await Promise.all([
        getAllPages((pageNumber) => getForecastHistory({ page: pageNumber, per_page: 100 })),
        getAllPages((pageNumber) => getPredictionHistory({ page: pageNumber, per_page: 100 })),
        getAllPages((pageNumber) => getAlertHistory({ page: pageNumber, per_page: 100 })),
        getAllPages((pageNumber) => getDetectionHistory({ page: pageNumber, per_page: 100 })),
      ]);
      if (currentRequest === requestId.current) {
        setRecords(toTimelineItems({ forecasts, assessments, alerts, detections }));
      }
    } catch {
      if (currentRequest === requestId.current) {
        setError("History could not be loaded. Please try again.");
      }
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    return () => {
      requestId.current += 1;
    };
  }, [load]);

  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return records.filter((item) => {
      const matchesActivity = activity === "all" || item.source === activity;
      const matchesRisk = !risk || String(item.result || "").toLocaleLowerCase().includes(risk.toLocaleLowerCase());
      const searchable = `${item.activity} ${item.location} ${item.result} ${item.description}`.toLocaleLowerCase();
      return matchesActivity && matchesRisk && (!query || searchable.includes(query));
    });
  }, [activity, records, risk, search]);

  const pageCount = Math.ceil(filtered.length / PAGE_SIZE);
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  async function remove(item) {
    const label = item.source === "assessment" ? "risk assessment" : "site detection";
    if (!window.confirm(`Delete this ${label} record?`)) return;
    setDeleting(`${item.source}:${item.id}`);
    setError("");
    setNotice("");
    try {
      if (item.source === "assessment") await deletePredictionHistory(item.id);
      else await deleteDetection(item.id);
      setNotice(`${label[0].toUpperCase()}${label.slice(1)} record deleted.`);
      await load();
    } catch {
      setError("The history record could not be deleted. Please try again.");
    } finally {
      setDeleting("");
    }
  }

  function exportCsv() {
    const rows = [
      ["Date", "Activity", "Location", "Result", "Confidence", "Details"],
      ...filtered.map((item) => [
        item.occurredAt,
        item.activity,
        item.location,
        item.result,
        item.confidence,
        item.description,
      ]),
    ];
    const csv = rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "dengue-forecast-history.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function updateFilter(setter, value) {
    setter(value);
    setPage(1);
  }

  return (
    <main className="dashboard-page history-page">
      <header className="page-intro history-toolbar">
        <div>
          <span className="page-overline">YOUR ACTIVITY</span>
          <h2>Forecast History</h2>
          <p>Forecasts, risk assessments, alerts, and site detections in one timeline.</p>
        </div>
        <div className="history-export-actions">
          <button type="button" className="btn btn-outline-primary" onClick={exportCsv} disabled={loading || !filtered.length}>
            <Download size={16} aria-hidden="true" /> Export CSV
          </button>
          <button type="button" className="btn btn-primary" onClick={() => window.print()} disabled={loading || !filtered.length}>
            <FileText size={16} aria-hidden="true" /> Export PDF
          </button>
        </div>
      </header>
      {error && <AlertMessage message={error} />}
      {notice && <AlertMessage message={notice} variant="success" onDismiss={() => setNotice("")} />}

      <section className="surface-card history-card">
        <div className="surface-heading">
          <div><h2>Activity timeline</h2><p>{filtered.length} matching records</p></div>
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={load} disabled={loading}>
            Refresh
          </button>
        </div>

        <div className="row g-2 mb-4 history-filters">
          <div className="col-lg-6">
            <label className="visually-hidden" htmlFor="history-search">Search history</label>
            <div className="input-group">
              <span className="input-group-text"><Search size={16} aria-hidden="true" /></span>
              <input
                id="history-search"
                className="form-control"
                value={search}
                onChange={(event) => updateFilter(setSearch, event.target.value)}
                placeholder="Search location, activity, result, or details"
              />
            </div>
          </div>
          <div className="col-sm-6 col-lg-3">
            <label className="visually-hidden" htmlFor="history-activity">Filter by activity</label>
            <select id="history-activity" className="form-select" value={activity} onChange={(event) => updateFilter(setActivity, event.target.value)}>
              <option value="all">All activity</option>
              <option value="forecast">AI Forecasts</option>
              <option value="assessment">Climate Risk Assessments</option>
              <option value="alert">Alerts</option>
              <option value="detection">Site Detections</option>
            </select>
          </div>
          <div className="col-sm-6 col-lg-3">
            <label className="visually-hidden" htmlFor="history-risk">Filter by result</label>
            <select id="history-risk" className="form-select" value={risk} onChange={(event) => updateFilter(setRisk, event.target.value)}>
              <option value="">All results</option>
              <option value="low">Low</option>
              <option value="moderate">Moderate</option>
              <option value="high">High</option>
              <option value="sent">Sent</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        {loading ? <LoadingSpinner label="Loading your history..." /> : pageItems.length ? (
          <>
            <div id="history-printable" className="history-timeline history-screen-only">
              {pageItems.map((item) => {
                const Icon = item.icon;
                const removable = ["assessment", "detection"].includes(item.source);
                return (
                  <article className="history-timeline-item" key={`${item.source}-${item.id}`}>
                    <span className="history-timeline-icon"><Icon size={18} aria-hidden="true" /></span>
                    <div className="history-timeline-content">
                      <div className="history-timeline-heading">
                        <div>
                          <h3>{item.activity}</h3>
                          <time dateTime={item.occurredAt}>{new Date(item.occurredAt).toLocaleString()}</time>
                        </div>
                        {item.source === "assessment"
                          ? <RiskIndicator level={item.result} />
                          : <span className={`badge text-bg-${["high", "failed"].includes(String(item.result).toLowerCase()) ? "danger" : "secondary"}`}>{item.result || "Recorded"}</span>}
                      </div>
                      <p className="history-timeline-location">{item.location}</p>
                      <p className="history-timeline-description">{item.description}</p>
                      {item.confidence != null && <small className="history-confidence">Confidence: {Number(item.confidence).toFixed(1)}%</small>}
                      {removable && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger history-delete"
                          aria-label={`Delete ${item.activity.toLowerCase()} record`}
                          disabled={Boolean(deleting)}
                          onClick={() => remove(item)}
                        >
                          <Trash2 size={14} aria-hidden="true" />
                          {deleting === `${item.source}:${item.id}` ? "Deleting…" : "Delete"}
                        </button>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
            <div className="history-print-only">
              <h1>Dengue Forecast History</h1>
              <p>{filtered.length} matching records</p>
              {filtered.map((item) => (
                <article key={`print-${item.source}-${item.id}`}>
                  <h2>{item.activity} — {item.result || "Recorded"}</h2>
                  <p>{new Date(item.occurredAt).toLocaleString()} · {item.location}</p>
                  <p>{item.description}</p>
                </article>
              ))}
            </div>
            <Pagination page={page} pageCount={pageCount} onChange={setPage} />
          </>
        ) : (
          <EmptyState
            icon={Activity}
            title={records.length ? "No matching history" : "No history yet"}
            description={records.length
              ? "Try changing the search or filters."
              : "Saved forecasts, risk assessments, alerts, and site detections will appear here."}
          />
        )}
      </section>
    </main>
  );
}
