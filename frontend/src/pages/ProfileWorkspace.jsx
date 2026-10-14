import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { FiHeart, FiPhone, FiShield, FiTrash2 } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import Profile from "./Profile.jsx";
import {
  createPrescription,
  deleteEmergencyContact,
  deletePrescription,
  getEmergencyContact,
  getPrescriptions,
  saveEmergencyContact,
  updatePrescription
} from "../services/patientRecordsService.js";
import { createEmergencyVCard, parseEmergencyVCard } from "../utils/emergencyVCard.js";

const EmergencyQrScanner = lazy(() => import("../components/EmergencyQrScanner.jsx"));

const today = new Date().toISOString().slice(0, 10);
const emptyPrescription = { medication: "", dose: "", instructions: "", prescriber: "", prescribed_date: today };

export default function ProfileWorkspace() {
  const [contact, setContact] = useState({ name: "", phone: "" });
  const [savedContact, setSavedContact] = useState(null);
  const [prescriptions, setPrescriptions] = useState([]);
  const [form, setForm] = useState(emptyPrescription);
  const [editingId, setEditingId] = useState(null);
  const [showQr, setShowQr] = useState(false);
  const [showScanner, setShowScanner] = useState(false);
  const [scannedContact, setScannedContact] = useState(null);
  const [scanError, setScanError] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const loadRecords = useCallback(async () => {
    setLoading(true);
    try {
      const [savedContact, savedPrescriptions] = await Promise.all([getEmergencyContact(), getPrescriptions()]);
      const loadedContact = savedContact || { name: "", phone: "" };
      setContact(loadedContact);
      setSavedContact(savedContact);
      setPrescriptions(savedPrescriptions);
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Personal records could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadRecords(); }, [loadRecords]);

  async function saveContact(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const savedContact = await saveEmergencyContact({
        name: contact.name,
        phone: contact.phone
      });
      setContact(savedContact);
      setSavedContact(savedContact);
      setShowQr(false);
      setMessage("Emergency contact saved.");
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Emergency contact could not be saved.");
    }
  }

  async function removeContact() {
    try {
      await deleteEmergencyContact();
      setContact({ name: "", phone: "" });
      setSavedContact(null);
      setShowQr(false);
      setMessage("Emergency contact deleted.");
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Emergency contact could not be deleted.");
    }
  }

  async function savePrescription(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      if (editingId) await updatePrescription(editingId, form);
      else await createPrescription(form);
      setForm({ ...emptyPrescription, prescribed_date: today });
      setEditingId(null);
      setMessage("Clinician-issued prescription record saved.");
      await loadRecords();
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Prescription record could not be saved.");
    }
  }

  function editPrescription(item) {
    setEditingId(item.id);
    setForm({
      medication: item.medication,
      dose: item.dose,
      instructions: item.instructions,
      prescriber: item.prescriber,
      prescribed_date: item.prescribed_date
    });
  }

  async function removePrescription(id) {
    if (!window.confirm("Delete this prescription record?")) return;
    try {
      await deletePrescription(id);
      setMessage("Prescription record deleted.");
      await loadRecords();
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Prescription record could not be deleted.");
    }
  }

  const handleQrScan = useCallback((value) => {
    setShowScanner(false);
    const result = parseEmergencyVCard(value);
    if (!result) {
      setScanError("This QR code is not a valid emergency contact card.");
      return;
    }
    setScanError("");
    setScannedContact(result);
  }, []);

  const hasUnsavedContact = savedContact && (
    savedContact.name !== contact.name || savedContact.phone !== contact.phone
  );
  const qrValue = savedContact?.name && savedContact?.phone
    ? createEmergencyVCard(savedContact)
    : "";

  return (
    <>
      <Profile />
      <section className="container pb-5">
        {error && <AlertMessage message={error} />}
        {message && <p className="alert alert-success" role="status">{message}</p>}
        {loading && <p role="status">Loading personal records…</p>}
        <div className="row g-3">
          <div className="col-12">
            <section className="surface-card profile-extra-card">
              <div className="surface-heading"><div><h2><FiHeart className="me-2" />Clinician-issued prescriptions</h2><p>Store a transcription of instructions already provided by your clinician.</p></div></div>
              <p className="alert alert-warning">This feature does not recommend medicines, validate doses, or replace a clinician or pharmacist. Enter only information from an existing prescription.</p>
              <form className="row g-3" onSubmit={savePrescription}>
                <div className="col-md-4"><label className="form-label" htmlFor="prescription-medication">Medication</label><input id="prescription-medication" className="form-control" maxLength="200" value={form.medication} onChange={(event) => setForm((current) => ({ ...current, medication: event.target.value }))} required disabled={loading} /></div>
                <div className="col-md-4"><label className="form-label" htmlFor="prescription-dose">Dose as written</label><input id="prescription-dose" className="form-control" maxLength="200" value={form.dose} onChange={(event) => setForm((current) => ({ ...current, dose: event.target.value }))} disabled={loading} /></div>
                <div className="col-md-4"><label className="form-label" htmlFor="prescription-prescriber">Prescriber</label><input id="prescription-prescriber" className="form-control" maxLength="150" value={form.prescriber} onChange={(event) => setForm((current) => ({ ...current, prescriber: event.target.value }))} required disabled={loading} /></div>
                <div className="col-md-4"><label className="form-label" htmlFor="prescription-date">Prescription date</label><input id="prescription-date" className="form-control" type="date" value={form.prescribed_date} onChange={(event) => setForm((current) => ({ ...current, prescribed_date: event.target.value }))} required disabled={loading} /></div>
                <div className="col-md-8"><label className="form-label" htmlFor="prescription-instructions">Instructions as written</label><textarea id="prescription-instructions" className="form-control" maxLength="2000" rows="2" value={form.instructions} onChange={(event) => setForm((current) => ({ ...current, instructions: event.target.value }))} disabled={loading} /></div>
                <div className="col-12"><button className="btn btn-primary me-2" type="submit" disabled={loading}>{editingId ? "Update record" : "Save prescription record"}</button>{editingId && <button className="btn btn-outline-secondary" type="button" disabled={loading} onClick={() => { setEditingId(null); setForm({ ...emptyPrescription, prescribed_date: today }); }}>Cancel edit</button>}</div>
              </form>
              <div className="mt-4">
                {prescriptions.length === 0 ? <p className="text-secondary mb-0">No prescription records saved.</p> : prescriptions.map((item) => (
                  <article className="surface-card mb-2" key={item.id}>
                    <div className="surface-heading"><div><strong>{item.medication}</strong><p className="mb-1">{item.dose || "No dose recorded"} · {item.prescriber} · {item.prescribed_date}</p>{item.instructions && <small>{item.instructions}</small>}</div>
                      <div className="d-flex gap-2"><button className="btn btn-outline-primary btn-sm" type="button" onClick={() => editPrescription(item)}>Edit</button><button className="btn btn-outline-danger btn-sm" type="button" aria-label={`Delete ${item.medication}`} onClick={() => removePrescription(item.id)}><FiTrash2 /></button></div>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </div>
          <div className="col-lg-7">
            <section className="surface-card profile-extra-card">
              <div className="surface-heading"><div><h2><FiPhone className="me-2" />Emergency contact</h2><p>Private to your account until you choose to display its QR code.</p></div></div>
              <form onSubmit={saveContact}>
                <label className="form-label" htmlFor="emergency-contact">Contact name</label>
                <input id="emergency-contact" className="form-control mb-3" maxLength="150" value={contact.name} onChange={(event) => { setShowQr(false); setContact((current) => ({ ...current, name: event.target.value })); }} required disabled={loading} />
                <label className="form-label" htmlFor="emergency-phone">Phone number</label>
                <input id="emergency-phone" className="form-control mb-3" type="tel" maxLength="32" value={contact.phone} onChange={(event) => { setShowQr(false); setContact((current) => ({ ...current, phone: event.target.value })); }} required disabled={loading} />
                <button className="btn btn-primary me-2" type="submit" disabled={loading}>Save contact</button>
                <button className="btn btn-outline-secondary me-2" type="button" onClick={() => setShowQr((visible) => !visible)} disabled={loading || !qrValue || hasUnsavedContact}>{showQr ? "Hide QR code" : "Show emergency QR"}</button>
                <button className="btn btn-outline-danger" type="button" onClick={removeContact} disabled={loading || !contact.name}><FiTrash2 className="me-1" />Delete</button>
              </form>
              {hasUnsavedContact && <p className="small text-secondary mt-2 mb-0">Save your changes before displaying an updated QR code.</p>}
              <p className="small text-secondary mt-3"><FiShield className="me-1" />The QR contains this contact’s name and phone number. Anyone who scans a displayed QR can read them.</p>
              {showQr && qrValue && <div className="text-center mt-3"><QRCodeSVG value={qrValue} size={224} level="M" title="Emergency contact QR code" /><p className="small mt-2 mb-0">Scannable contact card · no health or account data encoded</p></div>}
              {scanError && <AlertMessage message={scanError} />}
              <div className="mt-4">
                <button
                  className="btn btn-outline-primary"
                  type="button"
                  onClick={() => { setScanError(""); setScannedContact(null); setShowScanner((visible) => !visible); }}
                >
                  {showScanner ? "Close QR scanner" : "Scan emergency QR"}
                </button>
                {showScanner && <div className="mt-3"><Suspense fallback={<p role="status">Loading QR scanner…</p>}><EmergencyQrScanner onScan={handleQrScan} /></Suspense><p className="small text-secondary">Allow camera access or choose an image containing an emergency contact QR. Scanned details are shown here only and are not saved automatically.</p></div>}
                {scannedContact && <div className="alert alert-info mt-3" role="status"><strong>Scanned emergency contact</strong><div>{scannedContact.name}</div><div>{scannedContact.phone}</div></div>}
              </div>
            </section>
          </div>
        </div>
      </section>
    </>
  );
}
