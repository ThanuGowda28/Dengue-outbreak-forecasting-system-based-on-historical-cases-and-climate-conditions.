import { useCallback, useEffect, useState } from "react";
import AlertMessage from "../components/AlertMessage.jsx";
import {
  deleteAdminPrediction,
  getAdminPrediction,
  getAdminPredictions
} from "../services/adminService.js";

export default function AdminPredictions() {
  const [predictions, setPredictions] = useState([]);
  const [risk, setRisk] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getAdminPredictions({ risk: risk || undefined, page, per_page: 20 });
      setPredictions(result.predictions);
      setPagination(result.pagination);
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Risk assessments could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [risk, page]);

  useEffect(() => { load(); }, [load]);

  async function remove(id) {
    if (!window.confirm("Delete this prediction record?")) return;
    try {
      await deleteAdminPrediction(id);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Risk assessment could not be deleted.");
    }
  }

  async function viewPrediction(id) {
    setError("");
    try {
      const result = await getAdminPrediction(id);
      setSelected(result.prediction);
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Risk assessment details could not be loaded.");
    }
  }

  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">ADMINISTRATION</span><h2>Risk assessment management</h2><p>Review or remove saved climate risk assessments.</p></div>
      {error && <AlertMessage message={error} />}
      <section className="surface-card">
        <div className="surface-heading"><h3 className="h5">All risk assessments</h3><select aria-label="Filter by risk" className="form-select" value={risk} onChange={(event) => { setPage(1); setRisk(event.target.value); }}><option value="">All risk levels</option><option>Low</option><option>Moderate</option><option>High</option></select></div>
        {loading ? <p role="status">Loading risk assessments…</p> : predictions.length === 0 ? <p className="text-secondary mb-0">No assessment records found.</p> : (
          <div className="table-responsive"><table className="table align-middle"><thead><tr><th>ID</th><th>User</th><th>State</th><th>Risk</th><th>Confidence</th><th>Created</th><th>Actions</th></tr></thead><tbody>
            {predictions.map((item) => <tr key={item.id}><td>{item.id}</td><td>{item.user_id}</td><td>{item.state}</td><td>{item.risk_level}</td><td>{item.confidence}%</td><td>{new Date(item.prediction_time).toLocaleString()}</td><td><div className="d-flex gap-2"><button className="btn btn-outline-primary btn-sm" type="button" onClick={() => viewPrediction(item.id)}>View</button><button className="btn btn-outline-danger btn-sm" type="button" onClick={() => remove(item.id)}>Delete</button></div></td></tr>)}
          </tbody></table></div>
        )}
        {pagination && pagination.total_pages > 1 && <div className="d-flex align-items-center justify-content-between mt-3"><span>Page {pagination.page} of {pagination.total_pages} · {pagination.total_items} assessments</span><div className="d-flex gap-2"><button className="btn btn-outline-primary btn-sm" type="button" disabled={!pagination.has_previous || loading} onClick={() => setPage((current) => current - 1)}>Previous</button><button className="btn btn-outline-primary btn-sm" type="button" disabled={!pagination.has_next || loading} onClick={() => setPage((current) => current + 1)}>Next</button></div></div>}
      </section>
      {selected && <section className="surface-card mt-3"><div className="surface-heading"><h3 className="h5">Risk Assessment #{selected.id}</h3><button className="btn btn-outline-secondary btn-sm" type="button" onClick={() => setSelected(null)}>Close</button></div><div className="row g-3">
        <Detail label="User ID" value={selected.user_id} /><Detail label="State" value={selected.state} /><Detail label="Year" value={selected.year} /><Detail label="Risk level" value={selected.risk_level} /><Detail label="Confidence" value={`${selected.confidence}%`} /><Detail label="Temperature" value={`${selected.temperature} °C`} /><Detail label="Humidity" value={`${selected.humidity}%`} /><Detail label="Rainfall" value={`${selected.rainfall} mm`} /><Detail label="Wind speed" value={selected.wind_speed} /><Detail label="Pressure" value={selected.pressure} /><Detail label="Solar radiation" value={selected.solar_radiation} />
      </div><h4 className="h6 mt-3">Risk probabilities</h4><div className="row g-2">{Object.entries(selected.class_probabilities || {}).map(([level, probability]) => <div className="col-md-4" key={level}><div className="border rounded p-2"><span className="d-block text-secondary">{level}</span><strong>{(Number(probability) * 100).toFixed(1)}%</strong></div></div>)}</div></section>}
    </div>
  );
}

function Detail({ label, value }) {
  return <div className="col-6 col-md-3"><small className="text-secondary d-block">{label}</small><strong>{value ?? "—"}</strong></div>;
}
