import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FiTrash2 } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import { Pagination } from "../components/DashboardComponents.jsx";
import DetectionResult from "../components/detection/DetectionResult.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import { deleteDetection, getDetectionHistory } from "../services/detectionService.js";
import "../styles/mosquito-detection.css";

export default function DetectionHistory() {
  const [result, setResult] = useState({ items: [], pagination: { page: 1, total_pages: 0, total_items: 0 } });
  const [filters, setFilters] = useState({ search: "", risk: "", start_date: "", end_date: "" });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [deleting, setDeleting] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setResult(await getDetectionHistory({
        page,
        per_page: 10,
        search: filters.search || undefined,
        risk: filters.risk || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined
      }));
    } catch (loadError) {
      setError(loadError.response?.data?.message || "Detection history could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => { load(); }, [load]);

  function updateFilter(key, value) {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  }

  async function remove(item) {
    if (!window.confirm("Delete this detection and its uploaded images?")) return;
    setDeleting(item.id);
    setError("");
    try {
      await deleteDetection(item.id);
      setNotice("Detection record and stored image deleted.");
      if (result.items.length === 1 && page > 1) setPage(page - 1);
      else setResult((current) => ({
        ...current,
        items: current.items.filter((entry) => entry.id !== item.id),
        pagination: { ...current.pagination, total_items: Math.max(0, current.pagination.total_items - 1) }
      }));
    } catch (deleteError) {
      setError(deleteError.response?.data?.message || "Detection record could not be deleted.");
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="dashboard-page mosquito-history-page">
      <div className="page-intro"><span className="page-overline">YOUR ACTIVITY</span><h2>Detection history</h2><p>Review prior image analyses and download a PDF report for each record.</p></div>
      {error && <AlertMessage message={error} />}
      {notice && <AlertMessage message={notice} variant="success" onDismiss={() => setNotice("")} />}
      <section className="surface-card detection-history-toolbar">
        <div className="row g-2">
          <div className="col-lg-4"><label className="visually-hidden" htmlFor="detection-search">Search detections</label><input id="detection-search" className="form-control" placeholder="Search prediction or object" value={filters.search} onChange={(event) => updateFilter("search", event.target.value)} /></div>
          <div className="col-lg-3"><label className="visually-hidden" htmlFor="detection-risk-filter">Filter by risk</label><select id="detection-risk-filter" className="form-select" value={filters.risk} onChange={(event) => updateFilter("risk", event.target.value)}><option value="">All risk levels</option><option>High Risk Breeding Site</option><option>Medium Risk Breeding Site</option><option>Low Risk</option><option>No Breeding Site Detected</option></select></div>
          <div className="col"><label className="visually-hidden" htmlFor="detection-from-date">From date</label><input id="detection-from-date" className="form-control" type="date" value={filters.start_date} onChange={(event) => updateFilter("start_date", event.target.value)} /></div>
          <div className="col"><label className="visually-hidden" htmlFor="detection-to-date">To date</label><input id="detection-to-date" className="form-control" type="date" value={filters.end_date} onChange={(event) => updateFilter("end_date", event.target.value)} /></div>
        </div>
      </section>
      {loading ? <LoadingSpinner label="Loading detection history…" /> : result.items.length ? (
        <div className="detection-history-list">
          {result.items.map((item) => (
            <article className="detection-history-entry" key={item.id}>
              <DetectionResult detection={item} />
              <div className="detection-history-delete"><button type="button" className="btn btn-outline-danger btn-sm" onClick={() => remove(item)} disabled={deleting === item.id}><FiTrash2 className="me-1" />{deleting === item.id ? "Deleting…" : "Delete record"}</button></div>
            </article>
          ))}
          <Pagination page={result.pagination.page || 1} pageCount={result.pagination.total_pages || 0} onChange={setPage} />
        </div>
      ) : <section className="surface-card detection-empty-state"><h3>No matching detections</h3><p>Completed image analyses will appear here.</p><Link to="/mosquito-detection" className="btn btn-primary btn-sm">Analyze an image</Link></section>}
    </div>
  );
}
