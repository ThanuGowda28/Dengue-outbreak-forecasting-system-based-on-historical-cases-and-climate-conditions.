const RISK_TONES = new Set(["low", "moderate", "high"]);

export function normalizeRiskTone(level) {
  const tone = String(level || "").trim().toLowerCase();
  return RISK_TONES.has(tone) ? tone : "unknown";
}
