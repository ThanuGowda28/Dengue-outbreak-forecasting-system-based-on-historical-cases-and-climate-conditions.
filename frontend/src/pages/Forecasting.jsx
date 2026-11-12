import { useCallback, useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { FiDownload, FiInfo, FiRefreshCw, FiTrendingUp } from "react-icons/fi";
import {
  Chart as ChartJS,
  CategoryScale,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip
} from "chart.js";
import { Line } from "react-chartjs-2";
import AlertMessage from "../components/AlertMessage.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import { getRiskColor } from "../components/risk-map/riskColors.js";
import { useAuth } from "../context/AuthContext.jsx";
import {
  createForecast,
  downloadForecastReport,
  getForecastHistory,
  getForecastMap,
  getForecastOptions,
  getForecastTrends
} from "../services/forecastingService.js";
import "../styles/forecasting.css";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

const CLIMATE_SERIES = [
  { key: "temperature", label: "Temperature (°C)", color: "#ef8354" },
  { key: "humidity", label: "Humidity (%)", color: "#3985c6" },
  { key: "rainfall", label: "Rainfall (mm)", color: "#258e83" },
  { key: "wind_speed", label: "Wind speed (m/s)", color: "#8a63b8" },
  { key: "solar_radiation", label: "Solar radiation (MJ/m²/day)", color: "#d19b20" }
];

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { intersect: false, mode: "index" },
  plugins: {
    legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 7 } },
    tooltip: { mode: "index", intersect: false }
  },
  scales: {
    x: { grid: { display: false } },
    y: { beginAtZero: false, grid: { color: "rgba(113, 139, 145, .13)" } }
  }
};
const climateChartOptions = {
  ...chartOptions,
  plugins: { ...chartOptions.plugins, legend: { display: false } },
  scales: {
    ...chartOptions.scales,
    y: { ...chartOptions.scales.y, ticks: { ...chartOptions.scales.y.ticks, maxTicksLimit: 4 } }
  }
};

const RISK_LEVEL = { Low: 1, Moderate: 2, High: 3, "Very High": 4 };
const RISK_LABELS = { 0: "", 1: "Low", 2: "Moderate", 3: "High", 4: "Very High" };
const riskChartOptions = {
  ...chartOptions,
  scales: {
    ...chartOptions.scales,
    y: {
      min: 0,
      max: 4,
      ticks: {
        stepSize: 1,
        callback: (value) => RISK_LABELS[value] || ""
      }
    }
  }
};

export default function Forecasting() {
  const { user } = useAuth();
  const [options, setOptions] = useState(null);
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [forecastYear, setForecastYear] = useState("");
  const [historyYears, setHistoryYears] = useState(5);
  const [trends, setTrends] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [history, setHistory] = useState([]);
  const [mapItems, setMapItems] = useState([]);
  const [showMap, setShowMap] = useState(false);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [loadingTrends, setLoadingTrends] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [mapLoading, setMapLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [downloadId, setDownloadId] = useState(null);

  const districts = useMemo(
    () => options?.districts_by_state?.[state] || [],
    [options, state]
  );

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await getForecastHistory());
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Forecast history could not be loaded.");
    }
  }, []);

  useEffect(() => {
    let active = true;
    getForecastOptions()
      .then((data) => {
        if (!active) return;
        setOptions(data);
        const preferredState = data.states.includes(user?.state) ? user.state : data.states[0];
        setState(preferredState || "");
        setForecastYear(String(data.forecast_years[0] || ""));
      })
      .catch((requestError) => {
        if (active) setError(requestError.response?.data?.message || "Forecasting data could not be loaded.");
      })
      .finally(() => {
        if (active) setLoadingOptions(false);
      });
    loadHistory();
    return () => { active = false; };
  }, [loadHistory, user?.state]);

  useEffect(() => {
    if (!state) return undefined;
    let active = true;
    setLoadingTrends(true);
    setError("");
    getForecastTrends(state, historyYears)
      .then((data) => {
        if (active) setTrends(data);
      })
      .catch((requestError) => {
        if (active) setError(requestError.response?.data?.message || "Climate trends could not be loaded.");
      })
      .finally(() => {
        if (active) setLoadingTrends(false);
      });
    return () => { active = false; };
  }, [state, historyYears]);

  async function submitForecast(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setSuccess("");
    try {
      const result = await createForecast({
        state,
        district: district || null,
        forecast_year: Number(forecastYear)
      });
      setForecast(result);
      setSuccess(`Forecast for ${result.state} (${result.forecast_year}) generated and saved.`);
      await loadHistory();
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Forecast could not be generated.");
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleMap() {
    const next = !showMap;
    setShowMap(next);
    if (!next || mapItems.length || !forecastYear) return;
    setMapLoading(true);
    setError("");
    try {
      setMapItems(await getForecastMap(Number(forecastYear)));
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Forecast map data could not be loaded.");
      setShowMap(false);
    } finally {
      setMapLoading(false);
    }
  }

  async function downloadReport(id) {
    setDownloadId(id);
    setError("");
    try {
      const blob = await downloadForecastReport(id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `dengue-forecast-${id}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Forecast PDF could not be downloaded.");
    } finally {
      setDownloadId(null);
    }
  }

  const climateLabels = (trends?.history || []).map((item) => item.year);

  const riskChart = useMemo(() => {
    const timeline = forecast?.timeline || [];
    return {
      labels: timeline.map((item) => item.year),
      datasets: [{
        label: "Historical / forecast risk index",
        data: timeline.map((item) => RISK_LEVEL[item.risk] || 0),
        borderColor: "#188579",
        backgroundColor: "rgba(24, 133, 121, .12)",
        pointBackgroundColor: timeline.map((item) => (
          item.kind === "forecast" ? getRiskColor(item.risk) : "#188579"
        )),
        pointRadius: 5,
        fill: true,
        tension: 0.25
      }]
    };
  }, [forecast]);

  if (loadingOptions) return <LoadingSpinner label="Loading forecasting data…" />;

  return (
    <div className="dashboard-page forecasting-page">
      <div className="page-intro forecasting-intro">
        <div>
          <span className="page-overline">HISTORICAL-TREND FORECASTING</span>
          <h2>Forecasting</h2>
          <p>Explore historical climate and dengue trends, then generate an independent, state-level directional forecast.</p>
        </div>
        <span className="forecast-method-badge"><FiInfo aria-hidden="true" /> Research estimate · not medical advice</span>
      </div>

      {error && <AlertMessage message={error} />}
      {success && <div className="alert alert-success" role="status">{success}</div>}

      <section className="surface-card forecast-controls">
        <div className="surface-heading">
          <div><h2><FiTrendingUp className="me-2" />Forecast setup</h2><p>Choose the location and horizon to review historical records and generate a forecast.</p></div>
        </div>
        <form className="forecast-form" onSubmit={submitForecast}>
          <label>
            <span>Forecast year</span>
            <select className="form-select" value={forecastYear} onChange={(event) => { setForecastYear(event.target.value); setMapItems([]); setShowMap(false); }} required>
              {(options?.forecast_years || []).map((year) => <option value={year} key={year}>{year}</option>)}
            </select>
          </label>
          <label>
            <span>State / Union Territory</span>
            <select className="form-select" value={state} onChange={(event) => { setState(event.target.value); setDistrict(""); setForecast(null); setMapItems([]); }} required>
              {(options?.states || []).map((item) => <option value={item} key={item}>{item}</option>)}
            </select>
          </label>
          <label>
            <span>District <small>(optional)</small></span>
            <select className="form-select" value={district} onChange={(event) => setDistrict(event.target.value)} disabled={!districts.length}>
              <option value="">State-level forecast</option>
              {districts.map((item) => <option value={item} key={item}>{item}</option>)}
            </select>
          </label>
          <button className="btn btn-primary forecast-submit" type="submit" disabled={submitting || !state}>
            {submitting ? <><span className="spinner-border spinner-border-sm me-2" />Generating…</> : "Generate forecast"}
          </button>
        </form>
        <p className="forecast-data-note">
          District selection is a location label only: source dengue and climate series are state-level, not district observations.
          {options?.available_years?.length ? ` Complete data currently spans ${options.available_years[0]}–${options.available_years.at(-1)}.` : ""}
        </p>
      </section>

      <div className="forecast-grid">
        <section className="surface-card forecast-climate-card">
          <div className="surface-heading">
            <div><h2>Climate trend summary</h2><p>{state || "Selected state"} · annual historical averages and rainfall totals</p></div>
            <div className="forecast-year-switch" role="group" aria-label="Climate history range">
              {[5, 10].map((count) => (
                <button type="button" key={count} className={historyYears === count ? "active" : ""} onClick={() => setHistoryYears(count)}>
                  Past {count} years
                </button>
              ))}
            </div>
          </div>
          {loadingTrends ? <LoadingSpinner label="Loading climate trends…" /> : trends?.history?.length ? (
            <>
              <div className="forecast-climate-charts">
                {CLIMATE_SERIES.map((series) => (
                  <div className="forecast-mini-chart" key={series.key}>
                    <div><strong>{series.label}</strong><span>{Number(trends.history.at(-1)[series.key]).toLocaleString(undefined, { maximumFractionDigits: 1 })}</span></div>
                    <div className="forecast-mini-chart-canvas">
                      <Line
                        data={{
                          labels: climateLabels,
                          datasets: [{
                            label: series.label,
                            data: trends.history.map((item) => item[series.key]),
                            borderColor: series.color,
                            backgroundColor: `${series.color}22`,
                            pointRadius: 2.5,
                            tension: 0.3,
                            fill: true
                          }]
                        }}
                        options={climateChartOptions}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="forecast-trend-cards">
                {CLIMATE_SERIES.map((series) => {
                  const latest = trends.history.at(-1);
                  const previous = trends.history.at(-2);
                  const change = previous ? latest[series.key] - previous[series.key] : 0;
                  return (
                    <div className="forecast-metric" key={series.key}>
                      <span style={{ background: series.color }} />
                      <small>{series.label}</small>
                      <strong>{Number(latest[series.key]).toLocaleString(undefined, { maximumFractionDigits: 1 })}</strong>
                      <em>{change > 0 ? "+" : ""}{Number(change).toLocaleString(undefined, { maximumFractionDigits: 1 })} vs prior year</em>
                    </div>
                  );
                })}
              </div>
              <small className="forecast-source-note">{trends.data_note} Ten-year view displays only available complete years.</small>
            </>
          ) : <p className="forecast-empty">No climate trend records are available for this selection.</p>}
        </section>

        <section className="surface-card forecast-result-card">
          <div className="surface-heading">
            <div><h2>Forecast result</h2><p>{forecast ? `${forecast.state}${forecast.district ? ` · ${forecast.district}` : ""}` : "Generate a forecast to view results"}</p></div>
            <FiTrendingUp className="surface-heading-icon" />
          </div>
          {forecast ? (
            <>
              <div className="forecast-risk-banner" style={{ "--forecast-risk": getRiskColor(forecast.risk) }}>
                <small>FORECAST YEAR {forecast.forecast_year}</small>
                <strong>{forecast.risk.toUpperCase()}</strong>
                <span>{forecast.confidence}% heuristic confidence</span>
              </div>
              <dl className="forecast-result-values">
                <div><dt>Expected trend</dt><dd>{forecast.expected_trend}</dd></div>
                <div><dt>Projected reported cases</dt><dd>{Number(forecast.projected_cases).toLocaleString()}</dd></div>
                <div><dt>Latest historical risk</dt><dd>{forecast.latest_historical_risk}</dd></div>
              </dl>
              <p className="forecast-risk-summary">{forecast.risk_summary}</p>
              <h3>Suggested public health actions</h3>
              <ul className="forecast-recommendations">{forecast.recommendations.map((item) => <li key={item}>{item}</li>)}</ul>
              <small className="forecast-source-note">{forecast.method}</small>
              <div className="forecast-chart forecast-risk-chart"><Line data={riskChart} options={riskChartOptions} /></div>
            </>
          ) : <p className="forecast-empty">Forecasts are generated from historical annual case trends; they are separate from the ensemble climate risk assessment.</p>}
        </section>
      </div>

      <section className="surface-card forecast-map-section">
        <div className="surface-heading">
          <div><h2>India forecast map</h2><p>Compare directional forecast categories across supported states and union territories.</p></div>
          <button className="btn btn-outline-primary btn-sm" type="button" onClick={toggleMap} disabled={mapLoading}>
            {mapLoading ? <><span className="spinner-border spinner-border-sm me-2" />Loading map…</> : showMap ? "Hide map" : "Show forecast map"}
          </button>
        </div>
        {showMap && mapItems.length > 0 && (
          <div className="forecast-map-wrap">
            <MapContainer center={[22.5, 79]} zoom={4} scrollWheelZoom={false} className="forecast-leaflet-map">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <ForecastMapBounds items={mapItems} />
              {mapItems.map((item) => (
                <CircleMarker
                  key={item.state}
                  center={[item.latitude, item.longitude]}
                  radius={8}
                  pathOptions={{ color: "#fff", weight: 2, fillColor: getRiskColor(item.risk), fillOpacity: 0.9 }}
                >
                  <Popup><div className="forecast-map-popup"><strong>{item.state}</strong><span>{item.forecast_year} outlook: <b style={{ color: getRiskColor(item.risk) }}>{item.risk}</b></span><span>{item.confidence}% heuristic fit indicator</span></div></Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
        )}
        {showMap && mapItems.length === 0 && !mapLoading && <p className="forecast-empty">No map forecasts are available.</p>}
        <div className="forecast-map-legend"><span><i style={{ background: "#22c55e" }} />Low</span><span><i style={{ background: "#eab308" }} />Moderate</span><span><i style={{ background: "#f97316" }} />High</span><span><i style={{ background: "#dc2626" }} />Very High</span></div>
      </section>

      <section className="surface-card forecast-history-section">
        <div className="surface-heading"><div><h2>Saved forecast reports</h2><p>Your recent forecasting runs</p></div><button className="btn btn-outline-primary btn-sm" type="button" onClick={loadHistory}><FiRefreshCw className="me-1" />Refresh</button></div>
        {history.length ? (
          <div className="table-responsive">
            <table className="table forecast-history-table">
              <thead><tr><th>Generated</th><th>Forecast year</th><th>Location</th><th>Risk</th><th>Trend</th><th>Report</th></tr></thead>
              <tbody>{history.map((item) => (
                <tr key={item.id}>
                  <td>{new Date(item.generated_at).toLocaleDateString()}</td>
                  <td>{item.forecast_year}</td>
                  <td>{item.district ? `${item.district}, ` : ""}{item.state}</td>
                  <td><span className="forecast-history-risk" style={{ color: getRiskColor(item.risk) }}>{item.risk}</span></td>
                  <td>{item.expected_trend}</td>
                  <td><button className="btn btn-sm btn-outline-secondary" type="button" onClick={() => downloadReport(item.id)} disabled={downloadId === item.id}><FiDownload className="me-1" />{downloadId === item.id ? "Preparing…" : "PDF"}</button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <p className="forecast-empty">Forecasts you generate will be saved here.</p>}
      </section>
      <div className="forecast-disclaimer"><FiInfo aria-hidden="true" />This module extrapolates trends from historical state-level data. It is an academic research estimate, not an operational outbreak warning or medical advice. Confidence is not a calibrated probability.</div>
    </div>
  );
}

function ForecastMapBounds({ items }) {
  const map = useMap();
  useEffect(() => {
    if (items.length) {
      map.fitBounds(items.map((item) => [item.latitude, item.longitude]), { padding: [24, 24] });
    }
  }, [items, map]);
  return null;
}
