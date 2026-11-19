import { useCallback, useEffect, useRef, useState } from "react";
import { FiActivity, FiAlertTriangle, FiDownload, FiInfo, FiTarget } from "react-icons/fi";
import { useAuth } from "../context/AuthContext.jsx";
import { getPredictionHistory, getPredictionModelInfo, submitPrediction } from "../services/predictionService.js";
import { getCurrentWeather, normalizeWeatherError } from "../services/weatherService.js";
import { Pagination, RiskIndicator } from "../components/DashboardComponents.jsx";
import AlertMessage from "../components/AlertMessage.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import VoiceClimateInput from "../components/VoiceClimateInput.jsx";
import NearbyHospitalRecommendation from "../components/hospitals/NearbyHospitalRecommendation.jsx";

const thisYear = new Date().getFullYear();
const emptyFields = { temperature: "", humidity: "", rainfall: "", wind_speed: "", pressure: "", solar_radiation: "", year: String(thisYear) };
const csvValue = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;

export default function Prediction() {
  const { user } = useAuth();
  const [modelInfo, setModelInfo] = useState(null);
  const [state, setState] = useState(user?.state || "Karnataka");
  const [fields, setFields] = useState(emptyFields);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState({ items: [], pagination: { page: 1, total_pages: 0, total_items: 0 } });
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [weatherSource, setWeatherSource] = useState("");
  const [weatherNote, setWeatherNote] = useState("");
  const requestId = useRef(0);
  const inputRevision = useRef(0);
  const skipNextWeatherPrefill = useRef(false);

  const loadHistory = useCallback(async (nextPage = page, currentSearch = search, currentRisk = riskFilter) => {
    const data = await getPredictionHistory({ page: nextPage, per_page: 10, search: currentSearch, risk: currentRisk || undefined });
    setHistory(data);
  }, [page, riskFilter, search]);

  useEffect(() => {
    let active = true;
    Promise.all([getPredictionModelInfo(), getPredictionHistory({ page: 1, per_page: 10 })])
      .then(([info, records]) => {
        if (!active) return;
        setModelInfo(info);
        setHistory(records);
        if (info.supported_states?.includes(user?.state)) setState(user.state);
        else if (info.supported_states?.length) setState(info.supported_states[0]);
      })
      .catch((loadError) => { if (active) setError(loadError.response?.data?.message || normalizeWeatherError(loadError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [user?.state]);

  useEffect(() => {
    if (!state) return undefined;
    let active = true;
    const id = ++requestId.current;
    const revisionAtRequest = inputRevision.current;
    const skipPrefill = skipNextWeatherPrefill.current;
    skipNextWeatherPrefill.current = false;
    setWeatherLoading(true);
    getCurrentWeather({ state })
      .then(({ current, source }) => {
        if (!active || id !== requestId.current) return;
        if (!skipPrefill && revisionAtRequest === inputRevision.current) {
          setFields((old) => ({
            ...old,
            temperature: current.temperature ?? old.temperature,
            humidity: current.humidity ?? old.humidity,
            rainfall: current.rainfall ?? old.rainfall,
            wind_speed: current.wind_speed ?? old.wind_speed,
            pressure: current.pressure ?? old.pressure
          }));
        }
        setWeatherSource(source || "");
        setWeatherNote("Current provider observations were prefilled where available. This model expects annual climate means and annual total rainfall; replace snapshot values with annual aggregates before interpreting a prediction.");
      })
      .catch((weatherError) => {
        if (active && id === requestId.current) {
          setWeatherSource("");
          setWeatherNote("Live weather could not be loaded. Enter annual climate summaries manually.");
        }
      })
      .finally(() => { if (active && id === requestId.current) setWeatherLoading(false); });
    return () => { active = false; };
  }, [state]);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      getPredictionHistory({ page, per_page: 10, search: search.trim(), risk: riskFilter || undefined })
        .then((data) => { if (active) setHistory(data); })
        .catch((historyError) => { if (active) setError(historyError.response?.data?.message || "Prediction history could not be loaded."); });
    }, search ? 300 : 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [page, search, riskFilter]);

  function updateField(event) {
    inputRevision.current += 1;
    setFields((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  function applyVoiceInput({ fields: voiceFields, state: voiceState }) {
    inputRevision.current += 1;
    skipNextWeatherPrefill.current = Boolean(voiceState && voiceState !== state);
    setFields((current) => ({ ...current, ...voiceFields }));
    if (voiceState && modelInfo?.supported_states?.includes(voiceState)) {
      setState(voiceState);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const prediction = await submitPrediction({ state, ...Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, Number(value)])) });
      setResult(prediction);
      setPage(1);
      await loadHistory(1, search, riskFilter);
    } catch (predictionError) {
      setError(predictionError.response?.data?.message || "Prediction could not be completed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function exportHistory() {
    setExporting(true);
    setError("");
    try {
      const first = await getPredictionHistory({ page: 1, per_page: 100, search: search.trim(), risk: riskFilter || undefined });
      const rows = [...first.items];
      for (let currentPage = 2; currentPage <= first.pagination.total_pages; currentPage += 1) {
        const next = await getPredictionHistory({ page: currentPage, per_page: 100, search: search.trim(), risk: riskFilter || undefined });
        rows.push(...next.items);
      }
      const columns = ["prediction_time", "state", "risk_level", "confidence", "temperature", "humidity", "rainfall", "wind_speed", "pressure", "solar_radiation", "year"];
      const csv = [
        columns.map(csvValue).join(","),
        ...rows.map((row) => columns.map((column) => csvValue(row[column])).join(",")),
      ].join("\r\n");
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "dengue-prediction-history.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (exportError) {
      setError(exportError.response?.data?.message || "Prediction history could not be exported.");
    } finally {
      setExporting(false);
    }
  }

  if (loading) return <LoadingSpinner label="Loading prediction service..." />;
  const supportedStates = modelInfo?.supported_states || [];

  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">CLIMATE-BASED OUTLOOK</span><h2>Prediction</h2><p>Submit annual climate summaries to the trained three-network soft-voting ensemble.</p></div>
      {error && <AlertMessage message={error} />}
      {result?.alerts?.length > 0 && <div className="alert alert-info" role="status">
        {result.alerts.map((alert) => `${alert.alert_type === "email" ? "Email" : "SMS"} ${alert.status === "failed" ? "failed. Please try again later." : "queued for delivery."}`).join(" ")}
      </div>}
      {result?.alert_message && <AlertMessage variant="warning" message={result.alert_message} />}
      {!modelInfo?.available && <AlertMessage variant="warning" message={modelInfo?.message || "The prediction model is not available."} />}
      <div className="row g-4 align-items-start">
        <div className="col-xl-6">
          <form className="surface-card prediction-form" onSubmit={handleSubmit}>
            <div className="surface-heading"><div><h2>Climate inputs</h2><p>Model year range: 2021-2026 - annual-resolution observations</p></div><span className="feature-icon feature-icon-teal"><FiActivity /></span></div>
            <div className="mb-3"><label className="form-label" htmlFor="prediction-state">State / UT</label><select id="prediction-state" className="form-select" value={state} onChange={(event) => setState(event.target.value)} required>{supportedStates.map((name) => <option key={name} value={name}>{name}</option>)}</select></div>
            <VoiceClimateInput supportedStates={supportedStates} onRecognized={applyVoiceInput} />
            {weatherLoading && <div className="weather-loading"><span className="spinner-border spinner-border-sm text-primary" role="status" />Loading available weather...</div>}
            {weatherNote && <div className="alert alert-info py-2"><FiInfo className="me-2" />{weatherNote}{weatherSource ? ` Source: ${weatherSource}.` : ""}</div>}
            <div className="row g-3">
              <div className="col-md-6"><ClimateInput name="temperature" label="Average temperature" unit="°C" value={fields.temperature} onChange={updateField} min="-90" max="65" required /></div>
              <div className="col-md-6"><ClimateInput name="humidity" label="Average humidity" unit="%" value={fields.humidity} onChange={updateField} min="0" max="100" required /></div>
              <div className="col-md-6"><ClimateInput name="rainfall" label="Annual total rainfall" unit="mm" value={fields.rainfall} onChange={updateField} min="0" max="20000" required /></div>
              <div className="col-md-6"><ClimateInput name="wind_speed" label="Average wind speed" unit="m/s" value={fields.wind_speed} onChange={updateField} min="0" max="100" required /></div>
              <div className="col-md-6"><ClimateInput name="pressure" label="Average surface pressure" unit="hPa" value={fields.pressure} onChange={updateField} min="300" max="1200" required /></div>
              <div className="col-md-6"><ClimateInput name="solar_radiation" label="Average solar radiation" unit="MJ/m²/day" value={fields.solar_radiation} onChange={updateField} min="0" max="60" required /></div>
              <div className="col-md-6"><ClimateInput name="year" label="Observation year" unit="year" value={fields.year} onChange={updateField} min="2021" max="2026" step="1" required /></div>
            </div>
            <div className="prediction-data-note"><FiAlertTriangle /><span>Research classification only. The model was trained on annual aggregates; it is not a real-time outbreak forecast or a substitute for public-health advice.</span></div>
            <button className="btn btn-primary btn-lg w-100" type="submit" disabled={submitting || !modelInfo?.available || weatherLoading}>{submitting ? "Generating..." : <><FiTarget className="me-2" />Predict risk</>}</button>
          </form>
        </div>
        <div className="col-xl-6">
          {result ? <PredictionResult prediction={result} district={user?.district} /> : <section className="surface-card prediction-result"><div className="result-empty"><span className="result-target"><FiTarget /></span><span className="page-overline">ENSEMBLE SOFT VOTING</span><h2>Prediction result</h2><p>Enter annual climate data and run all three trained neural networks.</p></div></section>}
        </div>
      </div>

      <section className="surface-card prediction-history-card mt-4">
        <div className="surface-heading"><div><h2>Prediction history</h2><p>{history.pagination.total_items || 0} saved records</p></div><button type="button" className="btn btn-outline-primary btn-sm" onClick={exportHistory} disabled={exporting || history.pagination.total_items === 0}><FiDownload className="me-2" />{exporting ? "Exporting..." : "Export CSV"}</button></div>
        <div className="row g-2 mb-3"><div className="col-md-8"><label className="visually-hidden" htmlFor="prediction-search">Search prediction history</label><input id="prediction-search" className="form-control" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search state / UT" /></div><div className="col-md-4"><label className="visually-hidden" htmlFor="risk-filter">Filter risk</label><select id="risk-filter" className="form-select" value={riskFilter} onChange={(event) => { setRiskFilter(event.target.value); setPage(1); }}><option value="">All risk levels</option><option value="Low">Low</option><option value="Moderate">Moderate</option><option value="High">High</option></select></div></div>
        {history.items.length ? <div className="table-responsive"><table className="table align-middle"><thead><tr><th>Time</th><th>State / UT</th><th>Risk</th><th>Confidence</th></tr></thead><tbody>{history.items.map((item) => <tr key={item.id}><td>{new Date(item.prediction_time).toLocaleString()}</td><td>{item.state}</td><td><RiskIndicator level={item.risk_level} /></td><td>{Number(item.confidence).toFixed(2)}%</td></tr>)}</tbody></table></div> : <p className="text-secondary">No prediction records match this search.</p>}
        <Pagination page={history.pagination.page || 1} pageCount={history.pagination.total_pages || 0} onChange={setPage} />
      </section>
    </div>
  );
}

function ClimateInput({ name, label, unit, value, onChange, ...props }) {
  return <><label className="form-label d-flex justify-content-between" htmlFor={`prediction-${name}`}><span>{label}</span><span className="input-unit">{unit}</span></label><input id={`prediction-${name}`} name={name} className="form-control" type="number" step="any" value={value} onChange={onChange} {...props} /></>;
}

function PredictionResult({ prediction, district }) {
  const highRisk = ["high", "very high", "high risk", "very high risk"].includes(
    String(prediction.risk_level || "").trim().toLowerCase(),
  );
  return <section className="surface-card prediction-result"><div className="prediction-result-head"><span className="page-overline">ENSEMBLE RESULT</span><RiskIndicator level={prediction.risk_level} /></div><h2>{prediction.risk_level} Risk</h2><p>{prediction.state} · {new Date(prediction.prediction_time).toLocaleString()}</p><div className="confidence-heading"><strong>Top-class probability (uncalibrated)</strong><strong>{Number(prediction.confidence).toFixed(2)}%</strong></div><div className="progress" role="progressbar" aria-valuenow={prediction.confidence} aria-valuemin="0" aria-valuemax="100"><div className="progress-bar bg-success" style={{ width: `${prediction.confidence}%` }} /></div><h3 className="mt-4">Class probabilities</h3>{Object.entries(prediction.class_probabilities).map(([name, probability]) => <div className="probability-row" key={name}><span>{name}</span><div className="progress"><div className={`progress-bar bg-${name.toLowerCase()}`} style={{ width: `${probability * 100}%` }} /></div><strong>{(probability * 100).toFixed(1)}%</strong></div>)}<h3 className="mt-4">Recommendations</h3><ul className="recommendation-list">{prediction.recommendations.map((item) => <li key={item}>{item}</li>)}</ul><p className="small text-secondary mt-3 mb-0">{prediction.model_warning}</p>{highRisk && <NearbyHospitalRecommendation district={district} state={prediction.state} />}</section>;
}
