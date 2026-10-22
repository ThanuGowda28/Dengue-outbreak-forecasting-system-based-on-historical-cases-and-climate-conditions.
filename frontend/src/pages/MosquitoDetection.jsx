import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FiMapPin, FiRefreshCw, FiSearch } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import UploadCard from "../components/detection/UploadCard.jsx";
import DetectionResult from "../components/detection/DetectionResult.jsx";
import { analyzeMosquitoImage } from "../services/detectionService.js";
import "../styles/mosquito-detection.css";

export default function MosquitoDetection() {
  const [file, setFile] = useState(null);
  const [detection, setDetection] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [location, setLocation] = useState({});
  const [district, setDistrict] = useState("");
  const [sharingLocation, setSharingLocation] = useState(false);
  const [originalPreview, setOriginalPreview] = useState("");

  useEffect(() => {
    if (!file) {
      setOriginalPreview("");
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setOriginalPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function analyze() {
    if (!file) {
      setError("Upload or capture a JPG, JPEG, or PNG image before analyzing.");
      return;
    }
    setLoading(true);
    setError("");
    setNotice("");
    setDetection(null);
    try {
      const response = await analyzeMosquitoImage(file, { ...location, district });
      setDetection(response);
      if (response.alert_message) setNotice(response.alert_message);
      else if (response.alerts?.some((alert) => alert.alert_type === "in_app")) {
        setNotice("High-risk result saved. An in-app notification was created; eligible email/SMS alerts are queued.");
      } else {
        setNotice("Image analysis completed and saved to your detection history.");
      }
    } catch (analysisError) {
      const status = analysisError.response?.status;
      const code = analysisError.response?.data?.code;
      if (status === 413) setError("Image exceeds the 10 MB upload limit.");
      else if (code === "model_unavailable") setError("Image analysis is temporarily unavailable because the trained mosquito detector is not installed or configured.");
      else setError(analysisError.response?.data?.message || "Image analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function shareLocation() {
    if (!navigator.geolocation) {
      setError("Location sharing is not supported by this browser.");
      return;
    }
    setSharingLocation(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setLocation({ latitude: coords.latitude, longitude: coords.longitude });
        setSharingLocation(false);
        setError("");
      },
      () => {
        setSharingLocation(false);
        setError("Location could not be accessed. Allow location permission and try again.");
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
    );
  }

  function reset() {
    setFile(null);
    setDetection(null);
    setError("");
    setNotice("");
    setLocation({});
    setDistrict("");
  }

  return (
    <div className="dashboard-page mosquito-detection-page">
      <div className="page-intro">
        <span className="page-overline">COMMUNITY PREVENTION</span>
        <h2>Mosquito breeding-site detection</h2>
        <p>Upload a clear photo of standing water or a container that may collect water. The model’s result is informational; inspect the site and follow local health guidance.</p>
      </div>
      {error && <AlertMessage message={error} />}
      {notice && <AlertMessage message={notice} variant="success" onDismiss={() => setNotice("")} />}
      <div className="mosquito-detection-layout">
        <div className="mosquito-detection-controls">
          <UploadCard file={file} onFileChange={(value) => { setFile(value); setDetection(null); setError(""); }} disabled={loading} />
          <section className="surface-card detection-location-card">
            <h3>Location (optional)</h3>
            <p>Share coordinates to help administrators review high-risk areas.</p>
            <div className="detection-location-actions">
              <button className="btn btn-outline-secondary btn-sm" type="button" onClick={shareLocation} disabled={sharingLocation}>
                <FiMapPin className="me-1" />{sharingLocation ? "Requesting location…" : location.latitude ? "Location attached" : "Share GPS location"}
              </button>
              {location.latitude && <button className="btn btn-link btn-sm" type="button" onClick={() => setLocation({})}>Remove</button>}
            </div>
            <label className="form-label mt-3" htmlFor="detection-district">District (optional)</label>
            <input id="detection-district" className="form-control" maxLength={100} value={district} onChange={(event) => setDistrict(event.target.value)} placeholder="e.g. Mysuru" />
          </section>
          <div className="detection-page-actions">
            <button type="button" className="btn btn-primary" onClick={analyze} disabled={loading || !file}>
              {loading ? <><span className="spinner-border spinner-border-sm me-2" role="status" />Analyzing image…</> : <><FiSearch className="me-2" />Analyze image</>}
            </button>
            <button type="button" className="btn btn-outline-secondary" onClick={reset} disabled={loading}><FiRefreshCw className="me-2" />Reset</button>
            <Link className="btn btn-link" to="/mosquito-detection/history">View detection history</Link>
          </div>
        </div>
        <div className="mosquito-detection-output" aria-live="polite">
          {detection ? <DetectionResult detection={detection} originalPreview={originalPreview} /> : (
            <section className="surface-card detection-empty-state">
              <span className="detection-empty-icon"><FiSearch /></span>
              <h3>Analysis results appear here</h3>
              <p>Upload a location photo and select Analyze image to see the model result and recommended actions.</p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
