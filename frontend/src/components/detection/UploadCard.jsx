import { useEffect, useRef, useState } from "react";
import { FiCamera, FiImage, FiUploadCloud, FiX } from "react-icons/fi";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png"];

export default function UploadCard({ file, onFileChange, disabled }) {
  const inputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [preview, setPreview] = useState("");
  const [dragging, setDragging] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!file) {
      setPreview("");
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (cameraOpen && streamRef.current && videoRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraOpen]);

  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  function chooseFile(candidate) {
    setError("");
    if (!candidate) return;
    const extension = candidate.name.split(".").pop()?.toLowerCase();
    const supportedType = ACCEPTED_TYPES.includes(candidate.type)
      || (!candidate.type && ["jpg", "jpeg", "png"].includes(extension));
    if (!supportedType) {
      onFileChange(null);
      setError("Choose a JPG, JPEG, or PNG image.");
      return;
    }
    if (candidate.size > MAX_BYTES) {
      onFileChange(null);
      setError("Image exceeds the 10 MB upload limit.");
      return;
    }
    onFileChange(candidate);
  }

  async function openCamera() {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Camera capture is not supported by this browser.");
      return;
    }
    try {
      streamRef.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false
      });
      setCameraOpen(true);
    } catch {
      setError("Camera access is unavailable. Check browser permissions or upload an image instead.");
    }
  }

  function closeCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraOpen(false);
  }

  function capture() {
    const video = videoRef.current;
    if (!video?.videoWidth || !video?.videoHeight) {
      setError("The camera is not ready yet.");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setError("The camera image could not be captured.");
      return;
    }
    context.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) {
        setError("The camera image could not be captured.");
        return;
      }
      chooseFile(new File([blob], "camera-capture.jpg", { type: "image/jpeg" }));
      closeCamera();
    }, "image/jpeg", 0.9);
  }

  return (
    <section className="surface-card detection-upload-card">
      <div className="detection-upload-heading">
        <span className="detection-icon"><FiImage /></span>
        <div><h3>Choose a site image</h3><p>JPG, JPEG, or PNG · up to 10 MB</p></div>
      </div>
      <div
        className={`detection-dropzone ${dragging ? "is-dragging" : ""}`}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files?.[0]); }}
      >
        {preview ? <img className="detection-preview" src={preview} alt="Selected site preview" /> : (
          <div className="detection-drop-prompt">
            <FiUploadCloud aria-hidden="true" />
            <strong>Drag and drop an image here</strong>
            <span>or choose a file from your device</span>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,.jpg,.jpeg,.png"
          className="visually-hidden"
          disabled={disabled}
          onChange={(event) => { chooseFile(event.target.files?.[0]); event.target.value = ""; }}
        />
      </div>
      <div className="detection-upload-actions">
        <button type="button" className="btn btn-outline-primary" onClick={() => inputRef.current?.click()} disabled={disabled}><FiUploadCloud className="me-2" />Upload image</button>
        <button type="button" className="btn btn-outline-primary" onClick={openCamera} disabled={disabled}><FiCamera className="me-2" />Camera capture</button>
        {file && <button type="button" className="btn btn-outline-secondary" onClick={() => onFileChange(null)} disabled={disabled}><FiX className="me-2" />Remove</button>}
      </div>
      {cameraOpen && (
        <div className="detection-camera">
          <video ref={videoRef} autoPlay playsInline aria-label="Live camera preview" />
          <div><button type="button" className="btn btn-primary" onClick={capture}>Capture image</button><button type="button" className="btn btn-outline-secondary" onClick={closeCamera}>Close camera</button></div>
        </div>
      )}
      {error && <p className="detection-form-error" role="alert">{error}</p>}
    </section>
  );
}
