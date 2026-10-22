import api from "./api.js";

export async function getAlertHistory(params = {}) {
  const { data } = await api.get("/alerts/history", { params });
  return data;
}

export async function sendPredictionAlerts(predictionId) {
  const { data } = await api.post("/alerts/send", { prediction_id: predictionId });
  return data;
}

export async function getAlertSettings() {
  const { data } = await api.get("/alerts/settings");
  return data.preferences;
}

export async function updateAlertSettings(preferences) {
  const { data } = await api.put("/alerts/settings", preferences);
  return data.preferences;
}

export async function getAdminAlertHistory(params = {}) {
  const { data } = await api.get("/alerts/admin/history", { params });
  return data;
}

export async function exportAdminAlerts(params = {}) {
  const { data } = await api.get("/alerts/admin/export", {
    params,
    responseType: "blob"
  });
  return data;
}
