import api from "./api.js";

export async function submitContactMessage(payload) {
  const { data } = await api.post("/contact", payload, { skipAuth: true });
  return data;
}
