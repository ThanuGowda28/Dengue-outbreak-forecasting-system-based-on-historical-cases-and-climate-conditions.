import api from "./api.js";

export async function getAdminDashboard() {
  const { data } = await api.get("/admin/dashboard");
  return data;
}

export async function getAdminReports(params = {}) {
  const { data } = await api.get("/admin/reports", { params });
  return data;
}

export async function getAdminDatasets() {
  const { data } = await api.get("/admin/datasets");
  return data;
}

export async function uploadAdminDataset(file) {
  const body = new FormData();
  body.append("file", file);
  const { data } = await api.post("/admin/datasets", body, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteAdminDataset(relativePath) {
  const encodedPath = relativePath.split("/").map(encodeURIComponent).join("/");
  const { data } = await api.delete(`/admin/datasets/${encodedPath}`);
  return data;
}

export async function getAdminClimateData(params = {}) {
  const { data } = await api.get("/admin/climate-data", { params });
  return data;
}

export async function startAdminModelTraining() {
  const { data } = await api.post("/admin/model-training");
  return data.job;
}

export async function getAdminModelTraining(jobId) {
  const { data } = await api.get(`/admin/model-training/${encodeURIComponent(jobId)}`);
  return data.job;
}

export async function getAdminUsers(params = {}) {
  const { data } = await api.get("/admin/users", { params });
  return data;
}

export async function createAdminUser(payload) {
  const { data } = await api.post("/admin/users", payload);
  return data;
}

export async function updateAdminUser(userId, payload) {
  const { data } = await api.patch(`/admin/users/${userId}`, payload);
  return data;
}

export async function deleteAdminUser(userId) {
  const { data } = await api.delete(`/admin/users/${userId}`);
  return data;
}

export async function getAdminPredictions(params = {}) {
  const { data } = await api.get("/admin/predictions", { params });
  return data;
}

export async function getAdminPrediction(predictionId) {
  const { data } = await api.get(`/admin/predictions/${predictionId}`);
  return data;
}

export async function deleteAdminPrediction(predictionId) {
  const { data } = await api.delete(`/admin/predictions/${predictionId}`);
  return data;
}
