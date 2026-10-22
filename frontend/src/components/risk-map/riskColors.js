const RISK_COLORS = {
  low: "#22c55e",
  medium: "#eab308",
  moderate: "#eab308",
  high: "#f97316",
  "very high": "#dc2626"
};

export function getRiskColor(risk) {
  return RISK_COLORS[String(risk).toLowerCase()] || "#64748b";
}
