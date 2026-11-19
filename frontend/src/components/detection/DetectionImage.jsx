import { useEffect, useState } from "react";
import { getDetectionImage } from "../../services/detectionService.js";

export default function DetectionImage({ detectionId, kind = "original", alt }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let objectUrl;
    getDetectionImage(detectionId, kind)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (active) setUrl(objectUrl);
      })
      .catch(() => {
        if (active) setError("Image unavailable");
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [detectionId, kind]);

  return url ? <img src={url} alt={alt} className="detection-image" /> : (
    <div className="detection-image-placeholder" role="status">
      {error || "Loading image…"}
    </div>
  );
}
