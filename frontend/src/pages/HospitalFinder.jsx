import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FiAlertTriangle, FiCrosshair, FiRefreshCw, FiShield } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import HospitalCard from "../components/hospitals/HospitalCard.jsx";
import HospitalDetailsModal from "../components/hospitals/HospitalDetailsModal.jsx";
import HospitalFilters from "../components/hospitals/HospitalFilters.jsx";
import HospitalMap from "../components/hospitals/HospitalMap.jsx";
import HospitalSearch from "../components/hospitals/HospitalSearch.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getHospitalLocation, getNearbyHospitals, searchHospitals } from "../services/hospitalService.js";
import "../styles/hospital-finder.css";

const INDIA_CENTER = [20.5937, 78.9629];
const defaultFilters = {
  distance_km: "25",
  type: "",
  min_rating: "",
  open_24x7: "",
  emergency: "",
  icu: "",
  blood_bank: "",
};

function readableError(error) {
  if (!navigator.onLine) return "You appear to be offline. Check your internet connection and try again.";
  return error.response?.data?.message || "Hospital information could not be loaded. Please try again.";
}

export default function HospitalFinder() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get("location") || [user?.district, user?.state].filter(Boolean).join(", ");
  const [query, setQuery] = useState(initialQuery);
  const [location, setLocation] = useState(null);
  const [items, setItems] = useState([]);
  const [filters, setFilters] = useState(defaultFilters);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
  const [notice, setNotice] = useState("");
  const [emergencyOpen, setEmergencyOpen] = useState(false);
  const center = useMemo(() => location ? [location.latitude, location.longitude] : INDIA_CENTER, [location]);

  const loadNearby = useCallback(async (params) => {
    setLoading(true);
    setError("");
    setWarning("");
    setNotice("");
    try {
      const data = await getNearbyHospitals({ ...filters, ...params });
      setItems(data.items || []);
      setLocation(data.location || null);
      setWarning(data.provider_warning || "");
      if (!data.items?.length) setNotice("No nearby facilities matched. Try a larger distance or fewer filters.");
    } catch (loadError) {
      setItems([]);
      setError(readableError(loadError));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    if (initialQuery) loadNearby({ location: initialQuery });
  }, []);

  useEffect(() => {
    function online() { setError(""); }
    function offline() { setError("You appear to be offline. Hospital search may not work until your connection returns."); }
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
    };
  }, []);

  function filterParams(nextFilters = filters) {
    return Object.fromEntries(Object.entries(nextFilters).filter(([, value]) => value !== ""));
  }

  async function findMyLocation() {
    setError("");
    setNotice("");
    if (!navigator.geolocation) {
      setError("This browser does not support location. Enter a city, district or PIN code instead.");
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(async (position) => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
      let reverse = null;
      try {
        reverse = await getHospitalLocation(lat, lon);
      } catch {
        setWarning("Your GPS position was found, but district details could not be retrieved.");
      }
      const nextLocation = { latitude: lat, longitude: lon, ...reverse };
      setLocation(nextLocation);
      setQuery([nextLocation.district, nextLocation.state].filter(Boolean).join(", ") || `${lat.toFixed(4)}, ${lon.toFixed(4)}`);
      await loadNearby({ latitude: lat, longitude: lon });
    }, (geoError) => {
      setLoading(false);
      if (geoError.code === geoError.PERMISSION_DENIED) {
        setError("Location permission was denied. Search by district, city or PIN code instead.");
      } else if (geoError.code === geoError.POSITION_UNAVAILABLE) {
        setError("Your current location is unavailable. Enter a district, city or PIN code instead.");
      } else {
        setError("Location lookup timed out. Try again or search manually.");
      }
    }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 });
  }

  async function handleSearch() {
    const term = query.trim();
    if (term.length < 2) return;
    setLoading(true);
    setError("");
    setWarning("");
    setNotice("");
    try {
      const data = await searchHospitals(term, filterParams());
      if (data.items?.length) {
        setItems(data.items);
        if (data.location) setLocation(data.location);
        setWarning(data.provider_warning || "");
        setNotice(data.location ? "" : "Search results are from saved nearby facility records.");
      } else {
        setItems([]);
        setNotice("No hospitals or clinics found. Try a different district, city or PIN code.");
      }
    } catch (searchError) {
      setItems([]);
      setError(readableError(searchError));
    } finally {
      setLoading(false);
    }
  }

  function applyFilters(nextFilters) {
    setFilters(nextFilters);
    const params = Object.fromEntries(Object.entries(nextFilters).filter(([, value]) => value !== ""));
    if (location) {
      loadNearby({ latitude: location.latitude, longitude: location.longitude, ...params });
    } else if (query.trim()) {
      loadNearby({ location: query.trim(), ...params });
    }
  }

  function refresh() {
    if (location) loadNearby({ latitude: location.latitude, longitude: location.longitude });
    else if (query.trim()) loadNearby({ location: query.trim() });
  }

  const nearest = items[0];
  return (
    <main className="dashboard-page hospital-finder-page">
      <div className="page-intro hospital-page-intro">
        <span className="page-overline">CARE NEAR YOU</span>
        <h2>Hospital finder</h2>
        <p>Locate nearby hospitals, clinics, blood banks and diagnostic services. Confirm availability by phone before travelling.</p>
        <button className="btn btn-outline-primary" type="button" onClick={findMyLocation} disabled={loading}><FiCrosshair /> Use my location</button>
      </div>
      {error && <AlertMessage variant="warning" message={error} />}
      {warning && <AlertMessage variant="warning" message={warning} />}
      {notice && <div className="alert alert-info" role="status">{notice}</div>}
      <div className="hospital-finder-layout">
        <section className="hospital-results-column">
          <HospitalSearch value={query} onChange={setQuery} onSearch={handleSearch} busy={loading} />
          <HospitalFilters values={filters} onChange={applyFilters} />
          <div className="hospital-results-heading">
            <div><h2>Nearby medical facilities</h2><p>{location?.display_name || [location?.district, location?.city, location?.state].filter(Boolean).join(", ") || "Search or share your location"}</p></div>
            <button className="btn btn-outline-primary btn-sm" type="button" onClick={refresh} disabled={loading || (!location && !query)}><FiRefreshCw /> Refresh</button>
          </div>
          {loading ? <div className="hospital-loading" role="status"><span className="spinner-border spinner-border-sm" /> Finding nearby hospitals…</div> : (
            <div className="hospital-card-list">
              {items.map((hospital) => <HospitalCard key={hospital.id} hospital={hospital} onSelect={setSelected} />)}
              {!items.length && !error && <div className="hospital-empty"><FiShield /><strong>No facilities to display</strong><span>Allow location access or search for a district, city or PIN code.</span></div>}
            </div>
          )}
        </section>
        <section className="hospital-map-panel surface-card" aria-label="Hospital locations map">
          <div className="surface-heading"><div><h2>Map</h2><p>{location ? "Your location and matching facilities" : "Map centered on India"}</p></div></div>
          <HospitalMap center={center} hospitals={items} onSelect={setSelected} />
          <div className="hospital-map-key"><span className="hospital-map-key-user" /> Your location <span className="hospital-map-key-facility" /> Medical facility</div>
        </section>
      </div>
      <section className="hospital-emergency-panel" aria-labelledby="emergency-title">
        <div><span className="hospital-emergency-icon"><FiAlertTriangle /></span><div><h2 id="emergency-title">Need urgent care?</h2><p>For a medical emergency in India, call 112. Call 108 for ambulance assistance.</p></div></div>
        <button className="btn btn-danger" type="button" disabled={!nearest} onClick={() => setEmergencyOpen((open) => !open)}>{emergencyOpen ? "Hide nearest facility" : "Emergency options"}</button>
        {emergencyOpen && nearest && <div className="hospital-emergency-details">
          <strong>Nearest listed facility: {nearest.name}</strong>
          <span>{nearest.distance_km} km · estimated {nearest.estimated_travel_minutes || Math.max(1, Math.ceil(nearest.distance_km / 25 * 60))} min by road at 25 km/h</span>
          <span>Emergency contact: {nearest.phone || "Not listed"} · Ambulance: {nearest.ambulance_phone || (nearest.ambulance ? "Call 108 (India ambulance)" : "Not listed")}</span>
          {nearest.blood_bank && <span>Blood bank: listed as available; confirm by phone.</span>}
          <div className="hospital-actions">
            {nearest.phone && <a className="btn btn-danger btn-sm" href={`tel:${nearest.phone}`}>Call hospital</a>}
            {nearest.ambulance_phone && <a className="btn btn-danger btn-sm" href={`tel:${nearest.ambulance_phone}`}>Call ambulance</a>}
            <a className="btn btn-outline-primary btn-sm" href={`https://www.google.com/maps/dir/?api=1&destination=${nearest.latitude},${nearest.longitude}`} target="_blank" rel="noreferrer">Get directions</a>
          </div>
          <small>Travel time is a rough distance-based estimate, not live traffic guidance. For urgent help, call 112/108.</small>
        </div>}
      </section>
      <p className="hospital-data-note">Facility details and service availability may be incomplete or out of date in OpenStreetMap. Confirm by phone; this directory is not an emergency dispatch service.</p>
      <p className="hospital-back-link"><Link to="/prediction">Return to dengue prediction</Link></p>
      <HospitalDetailsModal hospital={selected} onClose={() => setSelected(null)} />
    </main>
  );
}
