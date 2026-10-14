import api from "./api.js";

export async function getEmergencyContact() {
  const { data } = await api.get("/profile/emergency-contact");
  return data.contact;
}

export async function saveEmergencyContact(contact) {
  const { data } = await api.put("/profile/emergency-contact", contact);
  return data.contact;
}

export async function deleteEmergencyContact() {
  const { data } = await api.delete("/profile/emergency-contact");
  return data;
}

export async function getPrescriptions() {
  const { data } = await api.get("/prescriptions");
  return data.prescriptions;
}

export async function createPrescription(prescription) {
  const { data } = await api.post("/prescriptions", prescription);
  return data.prescription;
}

export async function updatePrescription(id, prescription) {
  const { data } = await api.put(`/prescriptions/${id}`, prescription);
  return data.prescription;
}

export async function deletePrescription(id) {
  const { data } = await api.delete(`/prescriptions/${id}`);
  return data;
}
