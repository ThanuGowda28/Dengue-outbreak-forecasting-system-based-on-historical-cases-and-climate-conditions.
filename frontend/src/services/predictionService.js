import api from "./api.js";

export async function submitPrediction(payload) {
  const { data } = await api.post("/prediction/predict", payload);
  return data;
}

export async function getPredictionHistory(params = {}) {
  const { data } = await api.get("/prediction/history", { params });
  return data;
}

export async function deletePredictionHistory(predictionId) {
  const { data } = await api.delete(`/prediction/history/${predictionId}`);
  return data;
}

export async function getLatestPrediction() {
  const { data } = await api.get("/prediction/latest");
  return data.prediction;
}
