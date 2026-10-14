import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { FiDatabase, FiTarget, FiTrash2, FiUpload } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import { EmptyState } from "../components/DashboardComponents.jsx";
import {
  getAdminClimateData,
  getAdminDatasets,
  getAdminModelStatus,
  uploadAdminDataset,
  deleteAdminDataset,
  startAdminModelTraining,
  getAdminModelTraining,
} from "../services/adminService.js";
import AdminUsers from "./AdminUsers.jsx";
import AdminPredictions from "./AdminPredictions.jsx";

function useLoad(loader, dependencies) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await loader());
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Administrator data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, dependencies);

  useEffect(() => { load(); }, [load]);
  return { data, error, loading, reload: load };
}

function DatasetPage() {
  const { data, error, loading, reload } = useLoad(getAdminDatasets, []);
  const [file, setFile] = useState(null);
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);
  const datasets = data?.datasets || [];
  async function upload(event) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setActionError("");
    try {
      await uploadAdminDataset(file);
      setFile(null);
      event.currentTarget.reset();
      await reload();
    } catch (requestError) {
      setActionError(requestError.response?.data?.message || "CSV upload failed.");
    } finally {
      setBusy(false);
    }
  }
  async function remove(relativePath) {
    if (!window.confirm(`Delete uploaded dataset ${relativePath}?`)) return;
    setBusy(true);
    setActionError("");
    try {
      await deleteAdminDataset(relativePath);
      await reload();
    } catch (requestError) {
      setActionError(requestError.response?.data?.message || "Uploaded dataset could not be deleted.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">ADMINISTRATION</span><h2>Dataset management</h2><p>Review available datasets and manage isolated CSV uploads. Model and preprocessing artifacts are not accepted as uploads.</p></div>
      {error && <AlertMessage message={error} />}
      {actionError && <AlertMessage message={actionError} />}
      <form className="surface-card mb-3" onSubmit={upload}>
        <label className="form-label" htmlFor="admin-dataset-file">Upload a CSV dataset</label>
        <div className="d-flex gap-2 flex-wrap">
          <input id="admin-dataset-file" className="form-control" type="file" accept=".csv,text/csv" onChange={(event) => setFile(event.target.files?.[0] || null)} disabled={busy} />
          <button className="btn btn-primary" type="submit" disabled={busy || !file}><FiUpload className="me-1" />{busy ? "Working…" : "Upload CSV"}</button>
        </div>
        <p className="small text-secondary mt-2 mb-0">Uploads are stored separately; they do not replace production datasets or model files.</p>
      </form>
      {loading ? <p role="status">Loading dataset inventory…</p> : datasets.length === 0 ? <EmptyState icon={FiDatabase} title="No dataset files found" description="No supported CSV or preprocessing files are present in the configured dataset directory." /> : (
        <section className="surface-card">
          <div className="surface-heading"><h3 className="h5">Available files</h3><span>{data.total_items} files</span></div>
          <div className="table-responsive"><table className="table align-middle"><thead><tr><th>File</th><th>Category</th><th>Relative path</th><th>Size</th><th>Last updated</th><th>Actions</th></tr></thead><tbody>
            {datasets.map((item) => <tr key={item.relative_path}><td>{item.name}</td><td>{item.category}</td><td><code>{item.relative_path}</code></td><td>{formatBytes(item.size_bytes)}</td><td>{formatDate(item.updated_at)}</td><td>{item.category === "uploads" && <button className="btn btn-outline-danger btn-sm" type="button" disabled={busy} onClick={() => remove(item.relative_path)} aria-label={`Delete ${item.name}`}><FiTrash2 /></button>}</td></tr>)}
          </tbody></table></div>
        </section>
      )}
    </div>
  );
}

function ClimatePage() {
  const [filters, setFilters] = useState({ district: "", provider: "", record_type: "" });
  const [page, setPage] = useState(1);
  const load = useCallback(
    () => getAdminClimateData({ ...filters, page, per_page: 20 }),
    [filters, page]
  );
  const { data, error, loading } = useLoad(load, [load]);
  const pagination = data?.pagination;
  const records = data?.records || [];

  function updateFilter(event) {
    setPage(1);
    setFilters((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">ADMINISTRATION</span><h2>Stored climate data</h2><p>Browse weather and climate records saved from configured providers.</p></div>
      {error && <AlertMessage message={error} />}
      <section className="surface-card mb-3"><div className="row g-3">
        <div className="col-md-4"><label className="form-label" htmlFor="admin-climate-district">District</label><input id="admin-climate-district" className="form-control" name="district" value={filters.district} onChange={updateFilter} placeholder="Filter district" /></div>
        <div className="col-md-4"><label className="form-label" htmlFor="admin-climate-provider">Provider</label><select id="admin-climate-provider" className="form-select" name="provider" value={filters.provider} onChange={updateFilter}><option value="">All providers</option><option value="openweather">OpenWeather</option><option value="nasa_power">NASA POWER</option></select></div>
        <div className="col-md-4"><label className="form-label" htmlFor="admin-climate-type">Record type</label><select id="admin-climate-type" className="form-select" name="record_type" value={filters.record_type} onChange={updateFilter}><option value="">All types</option><option value="current">Current</option><option value="forecast">Forecast</option><option value="history">History</option></select></div>
      </div></section>
      <section className="surface-card">
        <div className="surface-heading"><h3 className="h5">Climate records</h3><span>{pagination?.total_items ?? 0} total</span></div>
        {loading ? <p role="status">Loading climate data…</p> : records.length === 0 ? <EmptyState icon={FiDatabase} title="No climate records" description="No stored climate observations match these filters." /> : (
          <div className="table-responsive"><table className="table align-middle"><thead><tr><th>Location</th><th>District</th><th>Type</th><th>Provider</th><th>Temp.</th><th>Humidity</th><th>Rainfall</th><th>Observed</th></tr></thead><tbody>
            {records.map((row) => <tr key={row.id}><td>{row.location_name}</td><td>{row.district || "—"}</td><td>{row.record_type}</td><td>{row.provider}</td><td>{formatMeasurement(row.temperature, "°C")}</td><td>{formatMeasurement(row.humidity, "%")}</td><td>{formatMeasurement(row.rainfall, " mm")}</td><td>{formatDate(row.observed_at)}</td></tr>)}
          </tbody></table></div>
        )}
        {pagination && pagination.total_pages > 1 && <div className="d-flex align-items-center justify-content-between mt-3"><span>Page {pagination.page} of {pagination.total_pages}</span><div className="d-flex gap-2"><button className="btn btn-outline-primary btn-sm" type="button" disabled={!pagination.has_previous || loading} onClick={() => setPage((current) => current - 1)}>Previous</button><button className="btn btn-outline-primary btn-sm" type="button" disabled={!pagination.has_next || loading} onClick={() => setPage((current) => current + 1)}>Next</button></div></div>}
      </section>
    </div>
  );
}

function ModelPage() {
  const { data, error, loading } = useLoad(getAdminModelStatus, []);
  const [job, setJob] = useState(null);
  const [trainingError, setTrainingError] = useState("");
  const [starting, setStarting] = useState(false);
  const timerRef = useRef(null);
  useEffect(() => () => window.clearTimeout(timerRef.current), []);
  useEffect(() => {
    if (job?.status !== "running") return undefined;
    let active = true;
    timerRef.current = window.setTimeout(async () => {
      try {
        const nextJob = await getAdminModelTraining(job.id);
        if (active) setJob(nextJob);
      } catch (requestError) {
        if (active) setTrainingError(requestError.response?.data?.message || "Training status could not be loaded.");
      }
    }, 2000);
    return () => {
      active = false;
      window.clearTimeout(timerRef.current);
    };
  }, [job]);
  async function startTraining() {
    setStarting(true);
    setTrainingError("");
    try {
      setJob(await startAdminModelTraining());
    } catch (requestError) {
      setTrainingError(requestError.response?.data?.message || "Training could not be started.");
      if (requestError.response?.data?.job) setJob(requestError.response.data.job);
    } finally {
      setStarting(false);
    }
  }
  const artifacts = data?.artifacts || [];
  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">ADMINISTRATION</span><h2>Model training workspace</h2><p>Run the existing training pipeline against configured processed datasets. Training artifacts are isolated and do not replace the active inference model.</p></div>
      {error && <AlertMessage message={error} />}
      {trainingError && <AlertMessage message={trainingError} />}
      {loading ? <p role="status">Checking model artifacts…</p> : <>
        <section className="surface-card mb-3"><h3 className="h5">Inference readiness</h3><p className={data.inference_artifacts_present ? "text-success mb-1" : "text-danger mb-1"}>{data.inference_artifacts_present ? "Required files are present" : "Required files are missing"}</p><p className="text-secondary mb-1">Runtime model load verified: {data.runtime_load_verified ? "Yes" : "No"}</p><p className="text-secondary mb-3">Training job available: {data.training_job_available ? "Yes" : "No — processed train.csv and test.csv are required"}</p><button className="btn btn-primary" type="button" onClick={startTraining} disabled={!data.training_job_available || starting || job?.status === "running"}>{starting ? "Starting…" : job?.status === "running" ? "Training in progress…" : "Start isolated training run"}</button></section>
        {job && <section className="surface-card mb-3"><h3 className="h5">Training run: {job.status}</h3><p className="small text-secondary">Started {formatDate(job.started_at)} · {job.output_is_staged ? "Results are staged and have not changed the active model." : "The active model remains unchanged while training."}</p>{job.error && <AlertMessage message={job.error} />}{job.metrics && <pre className="small overflow-auto">{JSON.stringify({ ensemble_accuracy: job.metrics.ensemble_accuracy, ensemble_f1_macro: job.metrics.ensemble_f1_macro, dataset_summary: job.metrics.dataset_summary }, null, 2)}</pre>}<pre className="small overflow-auto mb-0" aria-label="Training output">{job.log || "Waiting for training output…"}</pre></section>}
        <section className="surface-card">
          <div className="surface-heading"><h3 className="h5">Artifacts</h3><FiTarget aria-hidden="true" /></div>
          <div className="table-responsive"><table className="table align-middle"><thead><tr><th>Artifact</th><th>Availability</th><th>Required for inference</th><th>Size</th><th>Last updated</th></tr></thead><tbody>
            {artifacts.map((item) => <tr key={item.name}><td>{item.name}</td><td>{item.available ? "Available" : "Missing"}</td><td>{item.required_for_inference ? "Yes" : "No"}</td><td>{item.available ? formatBytes(item.size_bytes) : "—"}</td><td>{item.available ? formatDate(item.updated_at) : "—"}</td></tr>)}
          </tbody></table></div>
        </section>
      </>}
      <p className="demo-disclaimer">Training runs require TensorFlow and the configured processed datasets. Results are staged for review and are not automatically deployed.</p>
    </div>
  );
}

function formatBytes(value) {
  if (!Number.isFinite(value)) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "—";
}

function formatMeasurement(value, unit) {
  return Number.isFinite(value) ? `${value}${unit}` : "—";
}

export default function AdminWorkspace() {
  const { pathname } = useLocation();
  if (pathname === "/users") return <AdminUsers />;
  if (pathname === "/admin/predictions") return <AdminPredictions />;
  if (pathname === "/climate-data") return <ClimatePage />;
  if (pathname === "/train-model") return <ModelPage />;
  return <DatasetPage />;
}
