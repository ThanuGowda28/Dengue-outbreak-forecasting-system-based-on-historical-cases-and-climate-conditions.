export default function LoadingSpinner({ label = "Loading…" }) {
  return (
    <div className="loading-screen" role="status" aria-live="polite">
      <span className="spinner-border text-primary" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
