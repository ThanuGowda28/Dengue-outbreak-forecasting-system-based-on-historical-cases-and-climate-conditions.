import api from "./api.js";

export async function getRiskMapData(options = {}) {
  const { data } = await api.get("/risk-map", { signal: options.signal });
  return data;
}
