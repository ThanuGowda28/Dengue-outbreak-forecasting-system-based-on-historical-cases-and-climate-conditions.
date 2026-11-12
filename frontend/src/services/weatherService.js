import api from "./api.js";
import { getApiErrorMessage } from "../utils/apiErrors.js";

export async function getDistricts() {
  const { data } = await api.get("/weather/districts");
  return data.districts;
}

export async function searchWeatherLocations(query, options = {}) {
  const { data } = await api.get("/weather/search", {
    params: { q: query },
    signal: options.signal
  });
  return data.locations;
}

export async function getCurrentWeather(location) {
  const { data } = await api.get("/weather/current", { params: location });
  return data;
}

export async function getWeatherForecast(location) {
  const { data } = await api.get("/weather/forecast", { params: location });
  return data;
}

export async function getWeatherHistory(location) {
  const { data } = await api.get("/weather/history", { params: location });
  return data;
}

export function getPastDateRange(days = 30) {
  const end = new Date();
  end.setUTCHours(0, 0, 0, 0);
  end.setUTCDate(end.getUTCDate() - 1);

  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - Math.max(0, days - 1));
  return {
    start_date: start.toISOString().slice(0, 10),
    end_date: end.toISOString().slice(0, 10)
  };
}

export function normalizeWeatherError(error) {
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    return "Internet unavailable. Reconnect to the internet and refresh weather data.";
  }
  if (error.response?.status === 429) {
    return "Too many weather requests. Please wait briefly and try again.";
  }
  if (error.response?.status === 503) {
    const message = error.response.data?.message || "";
    if (message.includes("OPENWEATHER_API_KEY")) {
      return "Live weather is not configured for this application. Please contact the administrator.";
    }
    return "The weather provider is temporarily unavailable. Please try again later.";
  }
  return error.response?.data?.message || getApiErrorMessage(
    error,
    "Weather data could not be loaded. Check your connection and try again."
  );
}
