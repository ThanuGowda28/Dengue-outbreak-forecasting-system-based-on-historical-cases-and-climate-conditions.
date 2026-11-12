import { useCallback, useEffect, useState } from "react";
import { FiDownload, FiEdit2, FiPlus, FiTrash2, FiUpload } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import { Pagination } from "../components/DashboardComponents.jsx";
import {
  deleteHospital,
  downloadHospitalCsv,
  getHospitalStatistics,
  getManagedHospitals,
  importHospitals,
  saveHospital,
} from "../services/hospitalService.js";
import "../styles/hospital-admin.css";

const emptyHospital = {
  name: "", address: "", district: "", city: "", state: "", pincode: "",
  latitude: "", longitude: "", phone: "", ambulance_phone: "", email: "",
  rating: "", hospital_type: "Hospital", opening_hours: "", website: "",
  emergency: false, icu: false, blood_bank: false, ambulance: false,
};

export default function AdminHospitals() {
  const [result, setResult] = useState({ items: [], pagination: { page: 1, total_pages: 0, total_items: 0 } });
  const [statistics, setStatistics] = useState(null);
  const [form, setForm] = useState(emptyHospital);
  const [importFile, setImportFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);

  const load = useCallback(async (nextPage = page) => {
    setLoading(true);
    try {
      const [hospitals, stats] = await Promise.all([
        getManagedHospitals({ page: nextPage, per_page: 20 }),
        getHospitalStatistics(),
      ]);
      setResult(hospitals);
      setStatistics(stats);
      setError("");
    } catch (loadError) {
      setError(loadError.response?.data?.message || "Hospital records could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { load(page); }, [load, page]);

  function edit(hospital) {
    setForm({ ...hospital, latitude: String(hospital.latitude), longitude: String(hospital.longitude), rating: hospital.rating == null ? "" : String(hospital.rating) });
    setMessage("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function changeField(event) {
    const { name, value, checked, type } = event.target;
    setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await saveHospital({
        ...form,
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        rating: form.rating === "" ? null : Number(form.rating),
      });
      setForm(emptyHospital);
      setMessage("Hospital record saved.");
      await load(page);
    } catch (saveError) {
      setError(saveError.response?.data?.message || "Hospital record could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(hospital) {
    if (!window.confirm(`Delete ${hospital.name}?`)) return;
    setError("");
    try {
      await deleteHospital(hospital.id);
      setMessage(`${hospital.name} was deleted.`);
      await load(page);
    } catch (deleteError) {
      setError(deleteError.response?.data?.message || "Hospital could not be deleted.");
    }
  }

  async function importCsv(event) {
    event.preventDefault();
    if (!importFile) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const imported = await importHospitals(importFile);
      setMessage(imported.message);
      setImportFile(null);
      event.currentTarget.reset();
      await load(1);
      setPage(1);
    } catch (importError) {
      setError(importError.response?.data?.message || "Hospital CSV import failed.");
    } finally {
      setSaving(false);
    }
  }

  async function exportCsv() {
    setError("");
    try {
      const blob = await downloadHospitalCsv();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "hospitals.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (exportError) {
      setError(exportError.response?.data?.message || "Hospital records could not be exported.");
    }
  }

  return (
    <main className="dashboard-page">
      <div className="page-intro"><span className="page-overline">ADMINISTRATION</span><h2>Hospital management</h2><p>Maintain medical-facility details and review directory coverage. OpenStreetMap discoveries are refreshed when users search nearby.</p></div>
      {error && <AlertMessage message={error} />}
      {message && <div className="alert alert-success" role="status">{message}</div>}
      {statistics && <section className="hospital-stat-grid" aria-label="Hospital statistics">
        {[["Total facilities", statistics.total], ["Emergency", statistics.emergency], ["ICU", statistics.icu], ["Blood banks", statistics.blood_bank], ["Ambulance", statistics.ambulance]].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
      </section>}
      <section className="surface-card mb-4">
        <div className="surface-heading"><div><h2>{form.id ? "Edit hospital" : "Add a hospital"}</h2><p>Name and coordinates are required.</p></div></div>
        <form onSubmit={submit} className="hospital-admin-form">
          <label className="form-label">Hospital name<input className="form-control" name="name" value={form.name} onChange={changeField} maxLength={200} required /></label>
          <label className="form-label">Type<select className="form-select" name="hospital_type" value={form.hospital_type} onChange={changeField}>{["Government", "Private", "Hospital", "Clinic", "Blood Bank", "Diagnostic Lab", "Other"].map((type) => <option key={type}>{type}</option>)}</select></label>
          <label className="form-label">Address<input className="form-control" name="address" value={form.address} onChange={changeField} maxLength={500} /></label>
          <label className="form-label">District<input className="form-control" name="district" value={form.district || ""} onChange={changeField} maxLength={100} /></label>
          <label className="form-label">City<input className="form-control" name="city" value={form.city || ""} onChange={changeField} maxLength={100} /></label>
          <label className="form-label">State<input className="form-control" name="state" value={form.state || ""} onChange={changeField} maxLength={100} /></label>
          <label className="form-label">PIN code<input className="form-control" name="pincode" value={form.pincode || ""} onChange={changeField} maxLength={12} /></label>
          <label className="form-label">Latitude<input className="form-control" name="latitude" type="number" min="-90" max="90" step="any" value={form.latitude} onChange={changeField} required /></label>
          <label className="form-label">Longitude<input className="form-control" name="longitude" type="number" min="-180" max="180" step="any" value={form.longitude} onChange={changeField} required /></label>
          <label className="form-label">Phone<input className="form-control" name="phone" value={form.phone || ""} onChange={changeField} maxLength={40} /></label>
          <label className="form-label">Ambulance phone<input className="form-control" name="ambulance_phone" value={form.ambulance_phone || ""} onChange={changeField} maxLength={40} /></label>
          <label className="form-label">Email<input className="form-control" name="email" type="email" value={form.email || ""} onChange={changeField} maxLength={254} /></label>
          <label className="form-label">Google rating<input className="form-control" name="rating" type="number" min="0" max="5" step="0.1" value={form.rating} onChange={changeField} /></label>
          <label className="form-label">Working hours<input className="form-control" name="opening_hours" value={form.opening_hours || ""} onChange={changeField} maxLength={500} placeholder="e.g. 24/7" /></label>
          <label className="form-label">Website<input className="form-control" name="website" type="url" value={form.website || ""} onChange={changeField} maxLength={500} /></label>
          <div className="hospital-admin-checks">{[["emergency", "Emergency services"], ["icu", "ICU"], ["blood_bank", "Blood bank"], ["ambulance", "Ambulance"]].map(([key, label]) => <label className="form-check" key={key}><input className="form-check-input" type="checkbox" name={key} checked={Boolean(form[key])} onChange={changeField} /><span>{label}</span></label>)}</div>
          <div className="hospital-admin-toolbar">
            <div className="d-flex gap-2"><button className="btn btn-primary" type="submit" disabled={saving}>{form.id ? <><FiEdit2 /> Update hospital</> : <><FiPlus /> Add hospital</>}</button>{form.id && <button className="btn btn-outline-secondary" type="button" onClick={() => setForm(emptyHospital)}>Cancel edit</button>}</div>
          </div>
        </form>
      </section>
      <section className="surface-card mb-4">
        <div className="surface-heading"><div><h2>Import or export</h2><p>CSV import requires name, latitude, and longitude columns.</p></div></div>
        <div className="hospital-admin-toolbar">
          <form className="d-flex flex-wrap gap-2 align-items-center" onSubmit={importCsv}>
            <label className="visually-hidden" htmlFor="hospital-csv">CSV file</label>
            <input id="hospital-csv" className="form-control" type="file" accept=".csv,text/csv" onChange={(event) => setImportFile(event.target.files?.[0] || null)} />
            <button className="btn btn-outline-primary" type="submit" disabled={!importFile || saving}><FiUpload /> Import CSV</button>
          </form>
          <button type="button" className="btn btn-outline-primary" onClick={exportCsv}><FiDownload /> Export CSV</button>
        </div>
      </section>
      <section className="surface-card">
        <div className="surface-heading"><div><h2>Facility directory</h2><p>{result.pagination.total_items || 0} saved facilities</p></div></div>
        {loading ? <p role="status">Loading hospital directory…</p> : result.items.length ? <div className="table-responsive"><table className="table align-middle"><thead><tr><th>Hospital</th><th>Location</th><th>Type</th><th>Emergency</th><th>Actions</th></tr></thead><tbody>{result.items.map((hospital) => <tr key={hospital.id}><td><strong>{hospital.name}</strong><br /><small>{hospital.phone || "Phone not listed"}</small></td><td>{[hospital.city, hospital.district, hospital.pincode].filter(Boolean).join(", ") || "Not listed"}</td><td>{hospital.hospital_type}</td><td>{hospital.emergency ? "Yes" : "No"}</td><td><div className="d-flex gap-2"><button className="btn btn-sm btn-outline-primary" type="button" onClick={() => edit(hospital)} aria-label={`Edit ${hospital.name}`}><FiEdit2 /></button><button className="btn btn-sm btn-outline-danger" type="button" onClick={() => remove(hospital)} aria-label={`Delete ${hospital.name}`}><FiTrash2 /></button></div></td></tr>)}</tbody></table></div> : <p className="text-secondary">No hospital records are saved yet.</p>}
        <Pagination page={result.pagination.page || 1} pageCount={result.pagination.total_pages || 0} onChange={setPage} />
      </section>
    </main>
  );
}
