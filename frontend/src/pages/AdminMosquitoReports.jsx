import { useCallback, useEffect, useState } from "react";
import { FiDownload } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import { Pagination } from "../components/DashboardComponents.jsx";
import DetectionImage from "../components/detection/DetectionImage.jsx";
import { exportAdminDetectionReports, getAdminDetectionReports } from "../services/detectionService.js";
import "../styles/mosquito-detection.css";
import "../styles/mosquito-detection.css";

const RISKS = ["High Risk Breeding Site", "Medium Risk Breeding Site", "Low Risk", "No Breeding Site Detected"];

export default function AdminMosquitoReports() {
  const [result, setResult] = useState({ items: [], pagination: { page: 1, total_pages: 0, total_items: 0 } });
  const [filters, setFilters] = useState({ search: "", risk: "", start_date: "", end_date: "" });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  const params = {
    page,
    per_page: 25,
    search: filters.search || undefined,
    risk: filters.risk || undefined,
    start_date: filters.start_date || undefined,
    end_date: filters.end_date || undefined
  };
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setResult(await getAdminDetectionReports(params));
    } catch (loadError) {
      setError(loadError.response?.data?.message || "Detection reports could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => { load(); }, [load]);

  function updateFilter(key, value) {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  }

  async function exportCsv() {
    setExporting(true);
    setError("");
    try {
      const blob = await exportAdminDetectionReports({
        search: filters.search || undefined,
        risk: filters.risk || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "mosquito-detection-reports.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (exportError) {
      setError(exportError.response?.data?.message || "The detection report export failed.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="dashboard-page mosquito-admin-page">
      <div className="page-intro"><span className="page-overline">ADMINISTRATION</span><h2>Mosquito detection reports</h2><p>Review submitted images and filter detection results across user accounts.</p></div>
      {error && <AlertMessage message={error} />}
      <section className="surface-card detection-admin-card">
        <div className="detection-admin-toolbar">
          <input className="form-control" aria-label="Search by user" placeholder="Search user, email, district" value={filters.search} onChange={(event) => updateFilter("search", event.target.value)} />
          <select className="form-select" aria-label="Filter by risk" value={filters.risk} onChange={(event) => updateFilter("risk", event.target.value)}><option value="">All risk levels</option>{RISKS.map((risk) => <option key={risk}>{risk}</option>)}</select>
          <input className="form-control" aria-label="From date" type="date" value={filters.start_date} onChange={(event) => updateFilter("start_date", event.target.value)} />
          <input className="form-control" aria-label="To date" type="date" value={filters.end_date} onChange={(event) => updateFilter("end_date", event.target.value)} />
          <button type="button" className="btn btn-primary btn-sm" onClick={exportCsv} disabled={exporting}><FiDownload className="me-1" />{exporting ? "Exporting…" : "Export CSV"}</button>
        </div>
        {loading ? <p role="status">Loading submitted image reports…</p> : result.items.length ? (
          <div className="table-responsive">
            <table className="table align-middle detection-admin-table">
              <thead><tr><th>User</th><th>Uploaded image</th><th>Annotated image</th><th>Prediction</th><th>Confidence</th><th>Objects detected</th><th>Date</th></tr></thead>
              <tbody>{result.items.map((item) => (
                <tr key={item.id}>
                  <td>{item.user?.name}<small className="d-block text-secondary">{item.user?.email}</small></td>
                  <td><DetectionImage detectionId={item.id} alt={`Uploaded image from ${item.user?.name || "user"}`} /></td>
                  <td>{item.has_annotation ? <DetectionImage detectionId={item.id} kind="annotated" alt="Annotated detection image" /> : "—"}</td>
                  <td><span className={`detection-risk-pill risk-${item.prediction.startsWith("High") ? "high" : item.prediction.startsWith("Medium") ? "medium" : item.prediction.startsWith("Low") ? "low" : "safe"}`}>{item.prediction}</span></td>
                  <td>{Number(item.confidence).toFixed(1)}%</td>
                  <td>{item.objects_detected?.join(", ") || "None"}</td>
                  <td>{new Date(item.created_at).toLocaleString()}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <p className="text-secondary">No reports match these filters.</p>}
        <Pagination page={result.pagination.page || 1} pageCount={result.pagination.total_pages || 0} onChange={setPage} />
      </section>
    </div>
  );
}
