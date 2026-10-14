import { useEffect, useRef, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { FiCloud, FiInfo, FiMapPin, FiThermometer } from "react-icons/fi";
import { getCurrentWeather, getDistricts, getPastDateRange, getWeatherHistory, normalizeWeatherError } from "../services/weatherService.js";
import { ChartCard } from "../components/DashboardComponents.jsx";
import AlertMessage from "../components/AlertMessage.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import { DengueLineChart } from "../components/TrendCharts.jsx";
import { getPredictionHistory } from "../services/predictionService.js";

export default function RiskMap() {
  const [districts, setDistricts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [predictionError, setPredictionError] = useState("");
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState("");
  const requestId = useRef(0);

  useEffect(() => {
    let active = true;
    getDistricts()
      .then((items) => {
        if (active) setDistricts(items);
      })
      .catch((loadError) => {
        if (active) setError(normalizeWeatherError(loadError));
      })
      .finally(() => {
        if (active) setInitialLoading(false);
      });
    return () => { active = false; };
  }, []);

  async function loadDistrict(district) {
    const id = ++requestId.current;
    setSelected(district);
    setCurrent(null);
    setHistory([]);
    setPredictions([]);
    setPredictionError("");
    setError("");
    setLoading(true);
    const params = { district: district.name, latitude: district.latitude, longitude: district.longitude, state: district.state || "Karnataka" };
    const [currentResult, historyResult, predictionResult] = await Promise.allSettled([
      getCurrentWeather(params),
      getWeatherHistory({
        ...params,
        ...getPastDateRange()
      }),
      getPredictionHistory({ search: params.state, page: 1, per_page: 5 }),
    ]);
    if (id !== requestId.current) return;
    if (currentResult.status === "fulfilled") setCurrent(currentResult.value);
    else setError(normalizeWeatherError(currentResult.reason));
    if (historyResult.status === "fulfilled") setHistory(historyResult.value.history || []);
    else if (currentResult.status === "fulfilled") setError(normalizeWeatherError(historyResult.reason));
    if (predictionResult.status === "fulfilled") setPredictions(predictionResult.value.items || []);
    else setPredictionError(predictionResult.reason.response?.data?.message || "Saved state-level predictions could not be loaded.");
    setLoading(false);
  }

  if (initialLoading) return <LoadingSpinner label="Loading Karnataka district coordinates…" />;

  const chartHistory = [...history].sort((a, b) => new Date(a.weather_date) - new Date(b.weather_date));

  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">GEOGRAPHIC WEATHER OVERVIEW</span><h2>Karnataka district map</h2><p>Select a district to load its current provider weather and stored climate history. Outbreak-risk classifications require a future validated prediction model.</p></div>
      {error && <AlertMessage message={error} />}
      <div className="row g-3 align-items-start">
        <div className="col-xl-8">
          <section className="surface-card map-card">
            <div className="surface-heading map-heading"><div><h2><FiMapPin className="me-2" />District locations</h2><p>{districts.length} Karnataka districts · markers show locations, not risk levels</p></div><span className="map-legend"><span><i className="legend-dot legend-weather" />Weather location</span></span></div>
            {districts.length ? <div className="map-container" aria-label="Interactive Karnataka district location map">
              <MapContainer center={[14.7, 76.2]} zoom={6} scrollWheelZoom={false} className="risk-leaflet-map">
                <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <FitKarnatakaBounds districts={districts} />
                {districts.map((district) => (
                  <CircleMarker
                    key={district.name}
                    center={[district.latitude, district.longitude]}
                    radius={selected?.name === district.name ? 10 : 7}
                    pathOptions={{ color: "#fff", weight: 2, fillColor: selected?.name === district.name ? "#e53935" : "#1976d2", fillOpacity: 0.88 }}
                    eventHandlers={{ click: () => loadDistrict(district) }}
                  >
                    <Popup><strong>{district.name}</strong><br /><span>District coordinate: {district.latitude.toFixed(3)}, {district.longitude.toFixed(3)}</span><br /><button type="button" className="map-popup-button" onClick={() => loadDistrict(district)}>Load weather and history</button></Popup>
                  </CircleMarker>
                ))}
              </MapContainer>
            </div> : <p className="small text-secondary mb-0">District coordinates could not be loaded.</p>}
            <div className="map-legend"><span><i className="legend-dot legend-weather" />District location</span><span><i className="legend-dot legend-selected" />Selected district</span><span className="map-legend-note"><FiInfo /> No dengue risk classification is currently calculated</span></div>
          </section>
        </div>
        <div className="col-xl-4">
          <section className="surface-card map-detail-card">
            <div className="surface-heading"><div><h2>{selected?.name || "District details"}</h2><p>{selected ? "Live provider data when available" : "Choose a marker to load local conditions"}</p></div><FiMapPin className="surface-heading-icon" /></div>
            {loading && <div className="weather-loading"><span className="spinner-border spinner-border-sm text-primary" role="status" />Loading selected district…</div>}
            {current && !loading && <div className="map-weather-values"><div><FiThermometer /><span><small>Temperature</small><strong>{current.current.temperature ?? "—"}°C</strong></span></div><div><FiCloud /><span><small>Humidity</small><strong>{current.current.humidity ?? "—"}%</strong></span></div><div><FiCloud /><span><small>Rainfall</small><strong>{current.current.rainfall ?? "—"} mm</strong></span></div><div><FiInfo /><span><small>Pressure</small><strong>{current.current.pressure ?? "—"} hPa</strong></span></div><p className="weather-source">Source: {current.source || "Weather provider"}</p></div>}
            {!selected && <p className="map-detail-empty">Weather and state-level prediction history will appear here after selecting a district.</p>}
            {selected && !current && !loading && <p className="map-detail-empty">Current weather is unavailable for this location.</p>}
          </section>
          <section className="surface-card map-detail-card mt-3">
            <ChartCard title="Climate history" subtitle={selected ? `${selected.name} · provider observations` : "Select a district"}>{chartHistory.length ? <DengueLineChart labels={chartHistory.map((row) => new Date(row.weather_date).toLocaleDateString(undefined, { month: "short", day: "numeric" }))} data={chartHistory.map((row) => row.temperature)} color="#1976d2" fill label="Temperature (°C)" /> : <div className="weather-empty-chart">{selected && !loading ? "No climate history is available." : "Select a map marker to load stored history."}</div>}</ChartCard>
          </section>
          {selected && <section className="surface-card map-detail-card mt-3"><div className="surface-heading"><div><h2>Saved state predictions</h2><p>{selected.state || "Karnataka"} · not district-level risk</p></div><FiInfo /></div>{predictionError ? <AlertMessage message={predictionError} /> : predictions.length ? <ul className="list-group list-group-flush">{predictions.map((item) => <li className="list-group-item d-flex justify-content-between gap-2" key={item.id}><span>{item.state} · {item.year}<small className="d-block text-secondary">{new Date(item.prediction_time).toLocaleDateString()}</small></span><strong>{item.risk_level}</strong></li>)}</ul> : <p className="map-detail-empty">No saved predictions for this state. Submit a prediction to add one to history.</p>}</section>}
        </div>
      </div>
      <p className="demo-disclaimer"><FiInfo /> Weather observations are provider data when available. Outbreak-risk classification is not implemented and must not be inferred from weather alone.</p>
    </div>
  );
}

function FitKarnatakaBounds({ districts }) {
  const map = useMap();
  useEffect(() => {
    if (districts.length) map.fitBounds(districts.map((district) => [district.latitude, district.longitude]), { padding: [24, 24] });
  }, [districts, map]);
  return null;
}
