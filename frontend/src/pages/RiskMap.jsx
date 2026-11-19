import { useCallback, useEffect, useRef, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { FiAlertCircle, FiCloud, FiInfo, FiMapPin, FiRefreshCw, FiThermometer } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import { ChartCard } from "../components/DashboardComponents.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import DistrictPopup from "../components/risk-map/DistrictPopup.jsx";
import MapLegend from "../components/risk-map/MapLegend.jsx";
import RiskMarker from "../components/risk-map/RiskMarker.jsx";
import { getRiskColor } from "../components/risk-map/riskColors.js";
import { DengueLineChart } from "../components/TrendCharts.jsx";
import { getPastDateRange, getCurrentWeather, getWeatherHistory, normalizeWeatherError } from "../services/weatherService.js";
import { getRiskMapData } from "../services/riskMapService.js";
import { getPredictionHistory } from "../services/predictionService.js";
import { getAdminHighRiskBreedingSites } from "../services/detectionService.js";
import { useAuth } from "../context/AuthContext.jsx";
import { Link } from "react-router-dom";
import "../styles/risk-map.css";

export default function RiskMap() {
  const { user } = useAuth();
  const isAdmin = user?.role?.toLowerCase() === "admin";
  const [districts, setDistricts] = useState([]);
  const [breedingSites, setBreedingSites] = useState([]);
  const [siteError, setSiteError] = useState("");
  const [selected, setSelected] = useState(null);
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [predictionError, setPredictionError] = useState("");
  const [mapError, setMapError] = useState("");
  const [weatherError, setWeatherError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const mapRequest = useRef(0);
  const detailRequest = useRef(0);

  const refreshRiskData = useCallback(async () => {
    const requestId = ++mapRequest.current;
    setRefreshing(true);
    setMapError("");
    try {
      const data = await getRiskMapData();
      if (!Array.isArray(data)) {
        throw new Error("The risk map service returned an invalid response.");
      }
      if (requestId === mapRequest.current) {
        if (!isAdmin) {
          setBreedingSites([]);
          setSiteError("");
        }
        setDistricts(data);
        setSelected((previous) => previous
          ? data.find((district) => (
            district.district === previous.district && district.state === previous.state
          )) || null
          : null);
        if (isAdmin) {
          try {
            setBreedingSites(await getAdminHighRiskBreedingSites());
            setSiteError("");
          } catch (error) {
            setSiteError(error.response?.data?.message || "High-risk breeding-site reports could not be loaded.");
          }
        }
      }
    } catch (error) {
      if (requestId === mapRequest.current) {
        setMapError(
          error.response?.data?.message
          || error.message
          || "District risk data could not be loaded. Please try again."
        );
      }
    } finally {
      if (requestId === mapRequest.current) setRefreshing(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    refreshRiskData();
    return () => {
      mapRequest.current += 1;
      detailRequest.current += 1;
    };
  }, [refreshRiskData]);

  async function loadDistrict(district) {
    const requestId = ++detailRequest.current;
    setSelected(district);
    setCurrent(null);
    setHistory([]);
    setPredictions([]);
    setPredictionError("");
    setWeatherError("");
    setDetailLoading(true);
    const params = {
      district: district.district,
      latitude: district.latitude,
      longitude: district.longitude,
      state: district.state || "Karnataka"
    };
    const [currentResult, historyResult, predictionResult] = await Promise.allSettled([
      getCurrentWeather(params),
      getWeatherHistory({ ...params, ...getPastDateRange() }),
      getPredictionHistory({ search: params.state, page: 1, per_page: 5 })
    ]);
    if (requestId !== detailRequest.current) return;
    if (currentResult.status === "fulfilled") setCurrent(currentResult.value);
    else setWeatherError(normalizeWeatherError(currentResult.reason));
    if (historyResult.status === "fulfilled") setHistory(historyResult.value.history || []);
    else if (currentResult.status === "fulfilled") setWeatherError(normalizeWeatherError(historyResult.reason));
    if (predictionResult.status === "fulfilled") setPredictions(predictionResult.value.items || []);
    else setPredictionError(predictionResult.reason.response?.data?.message || "Saved state-level predictions could not be loaded.");
    setDetailLoading(false);
  }

  const chartHistory = [...history].sort(
    (first, second) => new Date(first.weather_date) - new Date(second.weather_date)
  );

  return (
    <div className="dashboard-page">
      <div className="page-intro risk-map-heading">
        <div>
          <span className="page-overline">KARNATAKA &amp; ANDHRA PRADESH OUTBREAK OVERVIEW</span>
          <h2>Interactive Dengue Risk Map</h2>
          <p>District risk uses the ensemble model and rolling-year climate observations. Select a marker for climate details and recommended actions.</p>
        </div>
        <button
          className="btn btn-outline-primary risk-map-refresh"
          type="button"
          onClick={refreshRiskData}
          disabled={refreshing}
        >
          <FiRefreshCw className={refreshing ? "risk-map-refreshing" : ""} aria-hidden="true" />
          {refreshing ? "Refreshing…" : "Refresh data"}
        </button>
      </div>

      {mapError && <AlertMessage message={mapError} />}
      <div className="row g-3 align-items-start">
        <div className="col-xl-8">
          <section className="surface-card map-card">
            <div className="surface-heading map-heading">
              <div>
                <h2><FiMapPin className="me-2" />District dengue risk</h2>
                <p>{districts.length} district markers · select one for risk and climate details</p>
              </div>
            </div>
            <div className="map-container risk-map-container" aria-label="Interactive dengue risk map of Karnataka and Andhra Pradesh">
              {districts.length ? (
                <MapContainer center={[15.5, 78.5]} zoom={6} scrollWheelZoom={false} className="risk-leaflet-map">
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <FitDistrictBounds districts={districts} />
                  {districts.map((district) => (
                    <RiskMarker
                      key={`${district.state}-${district.district}`}
                      district={district}
                      selected={selected?.district === district.district && selected?.state === district.state}
                      onSelect={loadDistrict}
                    />
                  ))}
                  {isAdmin && breedingSites.map((site) => (
                    <CircleMarker
                      key={`breeding-site-${site.id}`}
                      center={[site.latitude, site.longitude]}
                      radius={10}
                      pathOptions={{ color: "#8f1d21", weight: 2, fillColor: "#d13c3c", fillOpacity: 0.9 }}
                    >
                      <Popup>
                        <div className="breeding-site-popup">
                          <strong>High-risk breeding-site report</strong>
                          <span>{site.district || "Location not specified"}</span>
                          <span>{Number(site.confidence).toFixed(1)}% detector confidence</span>
                          <span>{site.objects_detected?.join(", ") || "Potential breeding site"}</span>
                          <small>{new Date(site.created_at).toLocaleString()}</small>
                          <Link to="/admin/mosquito-detection">Review all reports</Link>
                        </div>
                      </Popup>
                    </CircleMarker>
                  ))}
                </MapContainer>
              ) : (
                <div className="risk-map-empty">
                  {refreshing
                    ? <LoadingSpinner label="Loading Karnataka district risk data…" />
                    : "District risk data is not available. Use Refresh data to try again."}
                </div>
              )}
              {districts.length > 0 && <MapLegend />}
            </div>
          </section>
          {isAdmin && <div className="risk-map-disclaimer">
            <i className="breeding-site-map-key" aria-hidden="true" />
            <span>{breedingSites.length} user-submitted high-risk breeding-site location(s) are shown in red.{siteError ? ` ${siteError}` : ""}</span>
          </div>}
          <div className="risk-map-disclaimer">
            <FiInfo aria-hidden="true" />
            <span>The displayed score is the model’s uncalibrated class confidence, not a validated probability or medical diagnosis. Climate inputs are rolling 12-month aggregates because that is the period used to train the existing ensemble model.</span>
          </div>
        </div>

        <div className="col-xl-4">
          <section className="surface-card map-detail-card">
            <div className="surface-heading">
              <div>
                <h2>{selected?.district || "District details"}</h2>
                <p>{selected ? "Modelled risk and climate conditions" : "Choose a district marker"}</p>
              </div>
              <FiMapPin className="surface-heading-icon" />
            </div>
            {selected && (
              <>
                <div className="risk-map-detail-pill" style={{ color: getRiskColor(selected.risk) }}>
                  <i style={{ backgroundColor: getRiskColor(selected.risk) }} aria-hidden="true" />
                  {selected.risk} dengue risk
                </div>
                <div className="risk-map-detail-values">
                  <DistrictPopup district={selected} />
                </div>
              </>
            )}
            {detailLoading && <div className="risk-map-spinner"><span className="spinner-border spinner-border-sm text-primary" role="status" />Loading live weather and history…</div>}
            {weatherError && <AlertMessage message={weatherError} />}
            {current && !detailLoading && (
              <div className="map-weather-values">
                <div><FiThermometer /><span><small>Current temperature</small><strong>{current.current.temperature ?? "—"}°C</strong></span></div>
                <div><FiCloud /><span><small>Current humidity</small><strong>{current.current.humidity ?? "—"}%</strong></span></div>
                <div><FiCloud /><span><small>Current rainfall</small><strong>{current.current.rainfall ?? "—"} mm</strong></span></div>
                <div><FiInfo /><span><small>Pressure</small><strong>{current.current.pressure ?? "—"} hPa</strong></span></div>
                <p className="weather-source">Source: {current.source || "Weather provider"}</p>
              </div>
            )}
            {!selected && <p className="map-detail-empty">Select a marker to view modelled risk, climate observations, and local weather.</p>}
          </section>

          <section className="surface-card map-detail-card mt-3">
            <ChartCard
              title="Climate history"
              subtitle={selected ? `${selected.district} · recent observations` : "Select a district"}
            >
              {chartHistory.length ? (
                <DengueLineChart
                  labels={chartHistory.map((row) => new Date(row.weather_date).toLocaleDateString(undefined, { month: "short", day: "numeric" }))}
                  data={chartHistory.map((row) => row.temperature)}
                  color="#1976d2"
                  fill
                  label="Temperature (°C)"
                />
              ) : (
                <div className="weather-empty-chart">
                  {selected && !detailLoading ? "No climate history is available." : "Select a map marker to load stored history."}
                </div>
              )}
            </ChartCard>
          </section>

          {selected && (
            <section className="surface-card map-detail-card mt-3">
              <div className="surface-heading">
                <div><h2>Saved state predictions</h2><p>{selected.state || "Karnataka"} · not district-level risk</p></div>
                <FiInfo />
              </div>
              {predictionError ? (
                <AlertMessage message={predictionError} />
              ) : predictions.length ? (
                <ul className="list-group list-group-flush">
                  {predictions.map((item) => (
                    <li className="list-group-item d-flex justify-content-between gap-2" key={item.id}>
                      <span>{item.state} · {item.year}<small className="d-block text-secondary">{new Date(item.prediction_time).toLocaleDateString()}</small></span>
                      <strong>{item.risk_level}</strong>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="map-detail-empty">
                  {predictionError || "No saved predictions for this state. Submit a prediction to add one to history."}
                </p>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

function FitDistrictBounds({ districts }) {
  const map = useMap();
  useEffect(() => {
    if (districts.length) {
      map.fitBounds(
        districts.map((district) => [district.latitude, district.longitude]),
        { padding: [24, 24] }
      );
    }
  }, [districts, map]);
  return null;
}
