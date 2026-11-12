export default function LoadingSpinner({ label = "Loading…" }) {
  return (
    <div className="loading-screen skeleton-loading-screen" role="status" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      <div className="loading-skeleton-content" aria-hidden="true">
        <span className="loading-skeleton-line loading-skeleton-kicker" />
        <span className="loading-skeleton-line loading-skeleton-heading" />
        <span className="loading-skeleton-line loading-skeleton-copy" />
        <div className="loading-skeleton-grid">
          <span /><span /><span />
        </div>
      </div>
    </div>
  );
}
