import { FiCheckCircle, FiAlertTriangle } from "react-icons/fi";
import DetectionImage from "./DetectionImage.jsx";
import DetectionReport from "./DetectionReport.jsx";

const RISK_CLASS = {
  "High Risk Breeding Site": "high",
  "Medium Risk Breeding Site": "medium",
  "Low Risk": "low",
  "No Breeding Site Detected": "safe"
};

export default function DetectionResult({ detection, originalPreview, showReport = true }) {
  if (!detection) return null;
  const riskClass = RISK_CLASS[detection.prediction] || "safe";
  return (
    <section className="surface-card detection-result-card">
      <div className="detection-result-heading">
        <span className={`detection-risk-icon risk-${riskClass}`}>
          {riskClass === "high" || riskClass === "medium" ? <FiAlertTriangle /> : <FiCheckCircle />}
        </span>
        <div><span className="page-overline">ANALYSIS RESULT</span><h3>{detection.prediction}</h3></div>
        <strong className={`detection-confidence confidence-${riskClass}`}>{Number(detection.confidence).toFixed(1)}%</strong>
      </div>
      <div className="detection-image-grid">
        <div><span>Original image</span>{originalPreview ? <img className="detection-image" src={originalPreview} alt="Original uploaded potential breeding site" /> : <DetectionImage detectionId={detection.id} alt="Original uploaded potential breeding site" />}</div>
        {detection.has_annotation && <div><span>Detected objects</span><DetectionImage detectionId={detection.id} kind="annotated" alt="Annotated image with model-detected objects" /></div>}
      </div>
      <div className="detection-result-details">
        <div><strong>Detected objects</strong><p>{detection.objects_detected?.length ? detection.objects_detected.join(", ") : "No target objects detected."}</p></div>
        <div><strong>Recommended actions</strong><ul>{(detection.recommendation || []).map((item) => <li key={item}>{item}</li>)}</ul></div>
        <small>Analyzed {new Date(detection.created_at).toLocaleString()}</small>
        {showReport && <DetectionReport detectionId={detection.id} />}
      </div>
    </section>
  );
}
