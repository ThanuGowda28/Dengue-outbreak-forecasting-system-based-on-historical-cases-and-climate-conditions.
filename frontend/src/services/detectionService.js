import api from "./api.js";

export async function analyzeMosquitoImage(file, location = {}) {
  const form = new FormData();
  form.append("image", file);
  for (const [key, value] of Object.entries(location)) {
    if (value !== undefined && value !== null && value !== "") form.append(key, value);
  }
  const { data } = await api.post("/mosquito-detection/analyze", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}

export async function getDetectionHistory(params = {}) {
  const { data } = await api.get("/mosquito-detection/history", { params });
  return data;
}

export async function deleteDetection(id) {
  const { data } = await api.delete(`/mosquito-detection/${id}`);
  return data;
}

export async function retryDetectionAlerts(id) {
  const { data } = await api.post(`/mosquito-detection/${id}/alerts`);
  return data;
}

export async function getDetectionImage(id, kind = "original") {
  const { data } = await api.get(`/mosquito-detection/${id}/image`, {
    params: kind === "annotated" ? { kind } : undefined,
    responseType: "blob"
  });
  return data;
}

export async function downloadDetectionReport(id) {
  const { data } = await api.get(`/mosquito-detection/${id}/report.pdf`, {
    responseType: "blob"
  });
  return data;
}

export async function getAdminDetectionReports(params = {}) {
  const { data } = await api.get("/mosquito-detection/admin/reports", { params });
  return data;
}

export async function getAdminHighRiskBreedingSites() {
  const { data } = await api.get("/mosquito-detection/high-risk-locations");
  return data;
}

export async function exportAdminDetectionReports(params = {}) {
  const { data } = await api.get("/mosquito-detection/admin/export", {
    params,
    responseType: "blob"
  });
  return data;
}
