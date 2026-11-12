import assert from "node:assert/strict";
import test from "node:test";
import { csvCell, toTimelineItems } from "./historyTimeline.js";

test("combines all history sources and sorts newest first", () => {
  const items = toTimelineItems({
    forecasts: [{ id: 1, generated_at: "2025-01-02T00:00:00Z", state: "Karnataka", risk: "Low" }],
    assessments: [{ id: 2, prediction_time: "2025-01-01T00:00:00Z", state: "Karnataka", risk_level: "High" }],
    alerts: [{ id: 3, created_at: "2025-01-04T00:00:00Z", status: "sent", message_preview: "Alert sent" }],
    detections: [{ id: 4, created_at: "2025-01-03T00:00:00Z", district: "Mysuru", prediction: "Low Risk" }],
  });

  assert.deepEqual(items.map((item) => item.source), ["alert", "detection", "forecast", "assessment"]);
  assert.equal(items[2].activity, "AI Forecast");
  assert.equal(items[3].activity, "Climate Risk Assessment");
});

test("CSV cells escape quotes and neutralize spreadsheet formulas", () => {
  assert.equal(csvCell('=SUM("A1")'), `"'=SUM(""A1"")"`);
  assert.equal(csvCell("normal text"), '"normal text"');
});
