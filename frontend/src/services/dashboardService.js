import api from "./api.js";

export async function getDashboard() {
  const { data } = await api.get("/dashboard");
  return data;
}

export async function getWeatherReport(params = {}) {
  const reports = [];
  let page = 1;
  let firstResponse;
  let hasNext = true;
  while (hasNext) {
    const { data } = await api.get("/reports/weather", {
      params: { ...params, page }
    });
    if (!firstResponse) firstResponse = data;
    reports.push(...(data.reports || []));
    hasNext = Boolean(data.pagination?.has_next);
    page += 1;
  }
  return {
    ...firstResponse,
    reports,
    pagination: firstResponse?.pagination
      ? { ...firstResponse.pagination, has_next: false }
      : undefined
  };
}

export async function getStatistics(params) {
  const { data } = await api.get("/reports/statistics", { params });
  return data;
}
