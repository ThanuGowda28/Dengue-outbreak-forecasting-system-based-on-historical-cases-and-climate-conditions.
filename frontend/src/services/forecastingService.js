import api from "./api.js";

export async function getForecastOptions() {
  const { data } = await api.get("/forecast/options");
  return data;
}

export async function getForecastTrends(state, years = 5) {
  const { data } = await api.get("/forecast/trends", { params: { state, years } });
  return data;
}

export async function createForecast(payload) {
  const { data } = await api.post("/forecast", payload);
  return data;
}

export async function getForecastHistory(params = {}) {
  const { data } = await api.get("/forecast/history", { params });
  return data;
}

export async function getForecastMap(year) {
  const { data } = await api.get("/forecast/map", { params: { year } });
  return data.items || [];
}

export async function downloadForecastReport(forecastId) {
  const { data } = await api.get(`/forecast/history/${forecastId}/report.pdf`, {
    responseType: "blob"
  });
  return data;
}
