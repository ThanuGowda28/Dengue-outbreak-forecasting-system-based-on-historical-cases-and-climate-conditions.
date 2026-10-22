import api from "./api.js";

export async function getNearbyHospitals(params = {}) {
  const { data } = await api.get("/hospitals/nearby", { params });
  return data;
}

export async function searchHospitals(query, params = {}) {
  const { data } = await api.get("/hospitals/search", {
    params: { ...params, query },
  });
  return data;
}

export async function getHospitalLocation(latitude, longitude) {
  const { data } = await api.get("/hospitals/location", {
    params: { latitude, longitude },
  });
  return data;
}

export async function getManagedHospitals(params = {}) {
  const { data } = await api.get("/hospitals/manage", { params });
  return data;
}

export async function saveHospital(hospital) {
  const { data } = hospital.id
    ? await api.put(`/hospitals/manage/${hospital.id}`, hospital)
    : await api.post("/hospitals/manage", hospital);
  return data;
}

export async function deleteHospital(id) {
  const { data } = await api.delete(`/hospitals/manage/${id}`);
  return data;
}

export async function importHospitals(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/hospitals/manage/import", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getHospitalStatistics() {
  const { data } = await api.get("/hospitals/manage/statistics");
  return data;
}

export async function downloadHospitalCsv() {
  const { data } = await api.get("/hospitals/manage/export", { responseType: "blob" });
  return data;
}
