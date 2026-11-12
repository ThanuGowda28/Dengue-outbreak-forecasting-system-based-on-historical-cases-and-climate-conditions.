import { Activity, BellRing, MapPin, Sparkles } from "lucide-react";

export function toTimelineItems({ forecasts, assessments, alerts, detections }) {
  return [
    ...forecasts.map((item) => ({
      id: item.id,
      source: "forecast",
      activity: "AI Forecast",
      occurredAt: item.generated_at,
      location: [item.district, item.state].filter(Boolean).join(", ") || "Location not specified",
      result: item.risk,
      confidence: item.confidence,
      description: `${item.projected_cases ?? "—"} projected cases in ${item.forecast_year}.`,
      icon: Sparkles,
    })),
    ...assessments.map((item) => ({
      id: item.id,
      source: "assessment",
      activity: "Climate Risk Assessment",
      occurredAt: item.prediction_time,
      location: item.state || "Location not specified",
      result: item.risk_level,
      confidence: item.confidence,
      description: `Annual climate assessment for ${item.year}.`,
      icon: Activity,
    })),
    ...alerts.map((item) => ({
      id: item.id,
      source: "alert",
      activity: "Alert",
      occurredAt: item.created_at,
      location: item.alert_type?.replaceAll("_", " ") || "Notification",
      result: item.status,
      confidence: null,
      description: item.message_preview || item.message || "Health notification",
      icon: BellRing,
    })),
    ...detections.map((item) => ({
      id: item.id,
      source: "detection",
      activity: "Site Detection",
      occurredAt: item.created_at,
      location: item.district || "Location not specified",
      result: item.risk_level || item.prediction,
      confidence: item.confidence,
      description: (item.objects_detected || []).join(", ") || "Mosquito breeding-site assessment",
      icon: MapPin,
    })),
  ].sort((first, second) => {
    const firstTime = new Date(first.occurredAt || 0).getTime();
    const secondTime = new Date(second.occurredAt || 0).getTime();
    return secondTime - firstTime;
  });
}

export function csvCell(value) {
  let text = String(value ?? "");
  if (/^[\s]*[=+\-@]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}
