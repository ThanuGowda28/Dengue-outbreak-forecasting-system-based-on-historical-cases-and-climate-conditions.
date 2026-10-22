const RISK_ITEMS = [
  { level: "Low", color: "#22c55e" },
  { level: "Medium", color: "#eab308" },
  { level: "High", color: "#f97316" },
  { level: "Very High", color: "#dc2626" }
];

export default function MapLegend() {
  return (
    <aside className="risk-map-legend" aria-label="Dengue risk map legend">
      <strong>Risk level</strong>
      {RISK_ITEMS.map(({ level, color }) => (
        <span key={level}>
          <i aria-hidden="true" style={{ backgroundColor: color }} />
          {level}
        </span>
      ))}
    </aside>
  );
}
