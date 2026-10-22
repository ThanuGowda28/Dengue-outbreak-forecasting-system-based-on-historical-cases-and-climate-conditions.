import { useState } from "react";
import { FiDownload } from "react-icons/fi";
import { downloadDetectionReport } from "../../services/detectionService.js";

export default function DetectionReport({ detectionId }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function download() {
    setLoading(true);
    setError("");
    try {
      const blob = await downloadDetectionReport(detectionId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `mosquito-detection-${detectionId}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError.response?.data?.message || "The PDF report could not be downloaded.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <span>
      <button type="button" className="btn btn-outline-primary btn-sm" onClick={download} disabled={loading}>
        <FiDownload className="me-1" />{loading ? "Preparing…" : "Download PDF"}
      </button>
      {error && <small className="detection-form-error d-block" role="alert">{error}</small>}
    </span>
  );
}
