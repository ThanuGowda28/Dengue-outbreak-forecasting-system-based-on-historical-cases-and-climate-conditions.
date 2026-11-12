import api from "./api.js";

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
