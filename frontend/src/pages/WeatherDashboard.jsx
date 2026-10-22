import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FiCloud, FiDroplet, FiMapPin, FiRefreshCw, FiSearch, FiSun } from "react-icons/fi";
import { ChartCard, WeatherCard as ForecastCard } from "../components/DashboardComponents.jsx";
import WeatherDashboardPanel from "../components/weather/WeatherDashboardPanel.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import AlertMessage from "../components/AlertMessage.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  getCurrentWeather,
  getDistricts,
  getPastDateRange,
  getWeatherForecast,
  getWeatherHistory,
  normalizeWeatherError,
  searchWeatherLocations
} from "../services/weatherService.js";
import "../styles/weather-dashboard.css";

const iconByCode = (code = "") => {
  if (code.startsWith("09") || code.startsWith("10") || code.startsWith("11")) return FiDroplet;
  if (code.startsWith("01")) return FiSun;
  return FiCloud;
};

const dateLabel = (date) => new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" }).format(new Date(`${date.slice(0, 10)}T12:00:00`));

export default function WeatherDashboard() {
  const { user } = useAuth();
  const [districts, setDistricts] = useState([]);
  const [remoteSuggestions, setRemoteSuggestions] = useState([]);
  const [suggestionError, setSuggestionError] = useState("");
  const [searchingSuggestions, setSearchingSuggestions] = useState(false);
  const [location, setLocation] = useState({ district: "", city: "", state: user?.state || "", latitude: "", longitude: "" });
  const [query, setQuery] = useState("");
  const [coordinateMode, setCoordinateMode] = useState(false);
  const [coordinates, setCoordinates] = useState({ latitude: "", longitude: "" });
  const [current, setCurrent] = useState(null);
  const [weatherMeta, setWeatherMeta] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingDistricts, setLoadingDistricts] = useState(true);
  const [error, setError] = useState("");
  const [forecastError, setForecastError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const requestId = useRef(0);

  useEffect(() => {
    let active = true;
    getDistricts()
      .then((items) => {
        if (!active) return;
        setDistricts(items);
        const profileDistrict = items.find((item) => item.name.toLowerCase() === user?.district?.toLowerCase());
        if (profileDistrict) {
          setLocation({ district: profileDistrict.name, city: profileDistrict.name, state: user?.state || profileDistrict.state || "Karnataka", latitude: profileDistrict.latitude, longitude: profileDistrict.longitude });
          setQuery(profileDistrict.name);
        }
      })
      .catch((loadError) => {
        if (active) setError(normalizeWeatherError(loadError));
      })
      .finally(() => {
        if (active) setLoadingDistricts(false);
      });
    return () => { active = false; };
  }, [user?.district, user?.state]);

  useEffect(() => {
    const term = query.trim();
    const exactDistrict = districts.some(
      (district) => district.name.toLowerCase() === term.toLowerCase()
    );
    if (coordinateMode || term.length < 3 || exactDistrict) {
      setRemoteSuggestions([]);
      setSuggestionError("");
      setSearchingSuggestions(false);
      return undefined;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      setSearchingSuggestions(true);
      searchWeatherLocations(term, { signal: controller.signal })
        .then((items) => {
          setRemoteSuggestions(Array.isArray(items) ? items : []);
          setSuggestionError("");
        })
        .catch((searchError) => {
          if (controller.signal.aborted) return;
          setRemoteSuggestions([]);
          setSuggestionError(normalizeWeatherError(searchError));
        })
        .finally(() => {
          if (!controller.signal.aborted) setSearchingSuggestions(false);
        });
    }, 500);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [coordinateMode, districts, query]);

  const loadWeather = useCallback(async (place, { preserveCurrent = false } = {}) => {
    if (!place.district && !place.city && !(place.latitude && place.longitude)) return;
    const id = ++requestId.current;
    setLoading(true);
    setError("");
    setForecastError("");
    setHistoryError("");
    if (!preserveCurrent) {
      setWeatherMeta(null);
      setCurrent(null);
      setForecast([]);
      setHistory([]);
    }

    const locationParams = Object.fromEntries(
      Object.entries(place).filter(([, value]) => value !== "" && value !== null && value !== undefined)
    );
    const [currentResult, forecastResult, historyResult] = await Promise.allSettled([
      getCurrentWeather(locationParams),
      getWeatherForecast(locationParams),
      getWeatherHistory({
        ...locationParams,
        ...getPastDateRange()
      })
    ]);

    if (id !== requestId.current) return;
    if (currentResult.status === "fulfilled") {
      setCurrent(currentResult.value.current);
      setWeatherMeta(currentResult.value);
      setLastUpdated(currentResult.value.last_updated || new Date().toISOString());
    } else {
      setError(normalizeWeatherError(currentResult.reason));
    }
    if (forecastResult.status === "fulfilled") {
      setForecast(forecastResult.value.forecast || []);
    } else {
      setForecast([]);
      setForecastError(normalizeWeatherError(forecastResult.reason));
    }
    if (historyResult.status === "fulfilled") {
      setHistory(historyResult.value.history || []);
    } else {
      setHistory([]);
      setHistoryError(normalizeWeatherError(historyResult.reason));
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!loadingDistricts && (location.district || location.city || (location.latitude && location.longitude))) loadWeather(location);
  }, [loadingDistricts, location, loadWeather]);

  // Refresh provider observations periodically without clearing the last successful snapshot.
  useEffect(() => {
    if (loadingDistricts || (!location.district && !location.city && !(location.latitude && location.longitude))) return undefined;
    const interval = window.setInterval(
      () => loadWeather(location, { preserveCurrent: true }),
      30 * 60 * 1000
    );
    return () => window.clearInterval(interval);
  }, [loadingDistricts, loadWeather, location]);

  const suggestions = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return [];
    const districtSuggestions = districts
      .filter((district) => district.name.toLowerCase().includes(term))
      .map((district) => ({ ...district, label: district.name, detail: "Karnataka district" }));
    const knownDistricts = new Set(districtSuggestions.map((item) => item.name.toLowerCase()));
    const locationSuggestions = remoteSuggestions
      .filter((item) => item.name && !knownDistricts.has(item.name.toLowerCase()))
      .map((item) => ({
        ...item,
        label: [item.name, item.state, item.country].filter(Boolean).join(", "),
        detail: [item.state, item.country].filter(Boolean).join(" · ") || "Location"
      }));
    return [...districtSuggestions, ...locationSuggestions].slice(0, 8);
  }, [districts, query, remoteSuggestions]);

  function selectDistrict(district) {
    setQuery(district.name);
    const place = {
      district: district.name,
      city: district.name,
      state: "Karnataka",
      latitude: district.latitude,
      longitude: district.longitude
    };
    setLocation(place);
  }

  function selectSuggestion(suggestion) {
    const district = districts.find(
      (item) => item.name.toLowerCase() === suggestion.name?.toLowerCase()
    );
    if (district) {
      selectDistrict(district);
      return;
    }
    setQuery(suggestion.label);
    setLocation({
      city: suggestion.name,
      state: suggestion.state || "",
      latitude: suggestion.latitude,
      longitude: suggestion.longitude
    });
  }

  async function searchLocation(event) {
    event.preventDefault();
    if (coordinateMode) {
      const latitude = Number(coordinates.latitude);
      const longitude = Number(coordinates.longitude);
      if (!coordinates.latitude || !coordinates.longitude || !Number.isFinite(latitude) || latitude < -90 || latitude > 90 || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
        setError("Enter a latitude between -90 and 90 and a longitude between -180 and 180.");
        return;
      }
      setError("");
      setLocation({ latitude, longitude, state: location.state || "" });
      return;
    }
    const trimmed = query.trim();
    if (!trimmed) return;
    if (districts.some((district) => district.state.toLowerCase() === trimmed.toLowerCase())) {
      setError("Choose a district from the suggestions to load local weather for this state.");
      return;
    }
    const match = districts.find((district) => district.name.toLowerCase() === trimmed.toLowerCase());
    if (match) {
      selectDistrict(match);
      return;
    }
    const [city, ...stateParts] = trimmed.split(",");
    const state = stateParts.join(",").trim() || user?.state || location.state || "";
    const place = { city: city.trim(), ...(state ? { state } : {}) };
    setLocation(place);
  }

  const forecastByDay = groupForecastByDay(forecast);

  if (loadingDistricts) return <LoadingSpinner label="Loading district locations…" />;

  return (
    <div className="dashboard-page">
      <div className={`weather-live-hero ${current?.icon ? `weather-condition-${current.icon.slice(0, 2)}` : ""}`}>
        <div className="weather-live-heading">
          <div><span className="page-overline">LIVE WEATHER & CLIMATE</span><h2>{weatherMeta?.location?.district || weatherMeta?.location?.city || location.district || location.city || "Search a location"}</h2><p><FiMapPin /> {weatherMeta?.location?.state || location.state || "Select a Karnataka district or search a city"}</p></div>
          {current && <div className="weather-live-current"><div className="weather-live-temp"><span>{current.description || "Current conditions"}</span><strong>{current.temperature ?? "—"}°</strong></div><div className="weather-live-icon"><WeatherIcon icon={current.icon} /></div></div>}
        </div>
        <form className="weather-search" onSubmit={searchLocation}>
          {coordinateMode ? <div className="weather-coordinate-fields"><label><span>Latitude</span><input className="form-control" type="number" min="-90" max="90" step="any" value={coordinates.latitude} onChange={(event) => setCoordinates((current) => ({ ...current, latitude: event.target.value }))} required /></label><label><span>Longitude</span><input className="form-control" type="number" min="-180" max="180" step="any" value={coordinates.longitude} onChange={(event) => setCoordinates((current) => ({ ...current, longitude: event.target.value }))} required /></label></div> : <div className="weather-search-field"><FiSearch aria-hidden="true" /><input aria-label="Search district, city, or state" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search district or city, state (e.g. Mysuru, Karnataka)" list="weather-district-options" /><datalist id="weather-district-options">{districts.map((district) => <option key={district.name} value={district.name} />)}</datalist></div>}
          <div className="weather-search-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? "Loading…" : "Search weather"}</button>
            <button type="button" className="btn btn-outline-primary" onClick={() => loadWeather(location, { preserveCurrent: true })} disabled={loading || (!location.district && !location.city && !(location.latitude && location.longitude))} aria-label="Refresh weather">
              <FiRefreshCw aria-hidden="true" /> Refresh
            </button>
          </div>
        </form>
        {searchingSuggestions && <p className="weather-suggestion-status" role="status">Searching locations…</p>}
        {suggestionError && <p className="weather-suggestion-status text-danger" role="status">City suggestions are unavailable; you can still search this location manually.</p>}
        <button className="weather-coordinate-toggle" type="button" onClick={() => { setCoordinateMode((mode) => !mode); setError(""); }}>{coordinateMode ? "Search by city or district" : "Search by coordinates"}</button>
        {suggestions.length > 0 && query.trim() && !suggestions.some((item) => item.name.toLowerCase() === query.trim().toLowerCase()) && <div className="weather-suggestions" role="listbox" aria-label="Location suggestions">{suggestions.map((item) => <button type="button" role="option" key={`${item.name}-${item.latitude}-${item.longitude}`} onClick={() => selectSuggestion(item)}>{item.label}<small>{item.detail}</small></button>)}</div>}
      </div>

      {error && <AlertMessage message={error} />}
      {loading && <div className="weather-loading"><span className="spinner-border spinner-border-sm text-primary" role="status" /><span>Fetching provider weather data…</span></div>}
      {!current && !loading && !error && <AlertMessage message="No current weather was returned for this location." />}

      {current && <>
        <WeatherDashboardPanel
          current={current}
          history={history}
          forecast={forecast}
          lastUpdated={lastUpdated}
          historyError={historyError}
        />
        <section className="row g-3">
          <div className="col-12"><ChartCard title="Climate details" subtitle={`Provider observations${weatherMeta?.cached ? " · cached response" : ""}`}>
            <div className="weather-climate-details">
              <ClimateValue label="Feels like" value={current.feels_like} unit="°C" />
              <ClimateValue label="Pressure" value={current.pressure} unit="hPa" />
              <ClimateValue label="Cloud cover" value={current.cloud_cover} unit="%" />
              <ClimateValue label="Sunrise" value={current.sunrise} unit="" />
              <ClimateValue label="Sunset" value={current.sunset} unit="" />
              <ClimateValue label="Observation date" value={current.weather_date} unit="" />
              <p className="weather-source">Source: {weatherMeta?.source || "Weather provider"}{weatherMeta?.cached ? " · cached response" : ""}</p>
            </div>
          </ChartCard></div>
        </section>
      </>}

      <section className="surface-card">
        <div className="surface-heading"><div><h2>Forecast</h2><p>Provider forecast · hourly intervals grouped by day when available</p></div></div>
        {forecastError && <AlertMessage message={forecastError} />}
        {forecastByDay.length ? <div className="weather-forecast-grid">{forecastByDay.map((day) => <ForecastCard key={day.weather_date} day={dateLabel(day.weather_date)} icon={iconByCode(day.icon)} high={day.temperature == null ? "—" : Math.round(day.temperature)} low={day.temperature_min == null ? "—" : Math.round(day.temperature_min)} condition={day.description || "Conditions"} rain={day.rainfall != null ? `${day.rainfall} mm` : undefined} />)}</div> : <p className="mb-0 small text-secondary">Forecast is unavailable until a provider returns forecast data.</p>}
      </section>
      <p className="demo-disclaimer">Weather observations are informational and can be delayed or unavailable. They do not represent a dengue diagnosis or outbreak prediction.</p>
    </div>
  );
}

function WeatherIcon({ icon }) {
  const Icon = iconByCode(icon);
  return <Icon aria-hidden="true" />;
}

function ClimateValue({ label, value, unit }) {
  return <div className="climate-summary-row"><span>{label}</span><strong>{value === null || value === undefined || value === "" ? "Unavailable" : `${value}${unit ? ` ${unit}` : ""}`}</strong></div>;
}

function groupForecastByDay(entries) {
  const byDay = new Map();
  entries.forEach((entry) => {
    const date = entry.weather_date?.slice(0, 10);
    if (!date) return;
    const values = byDay.get(date) || [];
    values.push(entry);
    byDay.set(date, values);
  });

  return [...byDay.entries()].slice(0, 5).map(([weather_date, values]) => {
    const temperatures = values.map((value) => value.temperature).filter(Number.isFinite);
    const rainfall = values.map((value) => value.rainfall).filter(Number.isFinite);
    const average = (key) => {
      const numbers = values.map((value) => value[key]).filter(Number.isFinite);
      return numbers.length ? numbers.reduce((total, number) => total + number, 0) / numbers.length : null;
    };
    return {
      ...values[Math.floor(values.length / 2)],
      weather_date,
      temperature: temperatures.length ? Math.max(...temperatures) : null,
      temperature_min: temperatures.length ? Math.min(...temperatures) : null,
      rainfall: rainfall.length ? rainfall.reduce((total, amount) => total + amount, 0) : null,
      humidity: average("humidity"),
      pressure: average("pressure"),
      wind_speed: average("wind_speed"),
      cloud_cover: average("cloud_cover")
    };
  });
}
