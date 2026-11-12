import { useCallback, useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { FiCrosshair, FiMapPin, FiRefreshCw } from "react-icons/fi";
import { useAuth } from "../context/AuthContext.jsx";
import AlertMessage from "../components/AlertMessage.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import { getHospitalLocation, getNearbyHospitals, searchHospitals } from "../services/hospitalService.js";
import "../styles/hospital-finder.css";

const INDIA_CENTER = [20.5937, 78.9629];
const DEFAULT_FILTERS = {
  distance_km: "25",
  emergency: "",
  icu: "",
  blood_bank: "",
  ambulance: "",
};

function errorMessage(error) {
  if (!navigator.onLine) {
    return "You appear to be offline. Check your connection and try again.";
  }
  return error.response?.data?.message || "Hospital information could not be loaded. Please try again.";
}

function activeFilters(values) {
  return Object.fromEntries(
    Object.entries(values).filter(([, value]) => value !== ""),
  );
}

export default function HospitalFinder() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState(null);
  const [items, setItems] = useState([]);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [warning, setWarning] = useState("");
  const [notice, setNotice] = useState("");
  const center = useMemo(
    () => location ? [location.latitude, location.longitude] : INDIA_CENTER,
    [location],
  );

  const loadNearby = useCallback(async (params = {}) => {
    setLoading(true);
    setError("");
    setWarning("");
    setNotice("");
    try {
      const result = await getNearbyHospitals({ ...activeFilters(filters), ...params });
      setItems(result.items || []);
      setLocation(result.location || null);
      setWarning(result.provider_warning || "");
      if (!result.items?.length) {
        setNotice("No nearby facilities matched. Try a larger distance or fewer filters.");
      }
    } catch (loadError) {
      setItems([]);
      setError(errorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    const initialLocation = [user?.district, user?.state].filter(Boolean).join(", ");
    setQuery(initialLocation);
    if (!initialLocation) return undefined;

    let active = true;
    setLoading(true);
    getNearbyHospitals({ ...activeFilters(DEFAULT_FILTERS), location: initialLocation })
      .then((result) => {
        if (!active) return;
        setItems(result.items || []);
        setLocation(result.location || null);
        setWarning(result.provider_warning || "");
        if (!result.items?.length) {
          setNotice("No nearby facilities matched. Try a larger distance or fewer filters.");
        }
      })
      .catch((loadError) => {
        if (active) {
          setItems([]);
          setError(errorMessage(loadError));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [user?.district, user?.state]);

  async function search(event) {
    event.preventDefault();
    const term = query.trim();
    if (term.length < 2) {
      setError("Enter at least two characters for a location search.");
      return;
    }
    setLoading(true);
    setError("");
    setWarning("");
    setNotice("");
    try {
      const result = await searchHospitals(term, activeFilters(filters));
      setItems(result.items || []);
      setLocation(result.location || null);
      setWarning(result.provider_warning || "");
      if (!result.items?.length) setNotice("No hospitals or clinics found for this location.");
    } catch (searchError) {
      setItems([]);
      setError(errorMessage(searchError));
    } finally {
      setLoading(false);
    }
  }

  async function useMyLocation() {
    setError("");
    setNotice("");
    if (!navigator.geolocation) {
      setError("Location is not supported in this browser. Search by district, city or PIN code instead.");
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(async ({ coords }) => {
      const { latitude, longitude } = coords;
      try {
        let details = null;
        try {
          details = await getHospitalLocation(latitude, longitude);
        } catch {
          setWarning("Your location was found, but district details could not be retrieved.");
        }
        const result = await getNearbyHospitals({ ...activeFilters(filters), latitude, longitude });
        setLocation({ latitude, longitude, ...details });
        setQuery([details?.district, details?.state].filter(Boolean).join(", ") || `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`);
        setItems(result.items || []);
        setWarning(result.provider_warning || "");
        if (!result.items?.length) setNotice("No nearby facilities matched. Try a larger distance or fewer filters.");
      } catch (locationError) {
        setItems([]);
        setError(errorMessage(locationError));
      } finally {
        setLoading(false);
      }
    }, (locationError) => {
      setLoading(false);
      setError(locationError.code === locationError.PERMISSION_DENIED
        ? "Location permission was denied. Search by district, city or PIN code instead."
        : "Your location could not be retrieved. Search by district, city or PIN code instead.");
    }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 });
  }

  function updateFilter(event) {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function refresh() {
    if (location) {
      loadNearby({ latitude: location.latitude, longitude: location.longitude });
    } else if (query.trim()) {
      loadNearby({ location: query.trim() });
    }
  }

  return (
    <main className="dashboard-page hospital-finder-page">
      <div className="page-intro">
        <span className="page-overline">CARE NEAR YOU</span>
        <h2>Hospital finder</h2>
        <p>Search nearby hospitals and medical facilities. Confirm services and availability by phone before travelling.</p>
      </div>
      {error && <AlertMessage variant="warning" message={error} />}
      {warning && <AlertMessage variant="warning" message={warning} />}
      {notice && <div className="alert alert-info" role="status">{notice}</div>}

      <section className="surface-card hospital-finder-controls">
        <form className="hospital-finder-search" onSubmit={search}>
          <label className="form-label" htmlFor="hospital-location">City, district or PIN code</label>
          <div className="hospital-finder-search-row">
            <input
              id="hospital-location"
              className="form-control"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="For example, Mysuru, Karnataka"
              maxLength={160}
            />
            <button className="btn btn-primary" type="submit" disabled={loading || query.trim().length < 2}>Search</button>
            <button className="btn btn-outline-primary" type="button" onClick={useMyLocation} disabled={loading}>
              <FiCrosshair aria-hidden="true" /> Use my location
            </button>
          </div>
        </form>
        <div className="hospital-finder-filters">
          <label className="form-label" htmlFor="hospital-distance">Search radius</label>
          <select id="hospital-distance" className="form-select" name="distance_km" value={filters.distance_km} onChange={updateFilter}>
            {[5, 10, 25, 50, 100].map((distance) => <option key={distance} value={distance}>{distance} km</option>)}
          </select>
          {[
            ["emergency", "Emergency care"],
            ["icu", "ICU"],
            ["blood_bank", "Blood bank"],
            ["ambulance", "Ambulance"],
          ].map(([name, label]) => (
            <label className="hospital-filter-check" key={name}>
              <input
                type="checkbox"
                checked={filters[name] === "true"}
                onChange={(event) => updateFilter({ target: { name, value: event.target.checked ? "true" : "" } })}
              />
              {label}
            </label>
          ))}
          <button className="btn btn-outline-primary btn-sm" type="button" onClick={refresh} disabled={loading}>
            Apply filters
          </button>
        </div>
      </section>

      <div className="hospital-finder-results-heading">
        <div>
          <h3>Nearby medical facilities</h3>
          <p>{location?.display_name || [location?.district, location?.city, location?.state].filter(Boolean).join(", ") || "Search for a location to see facilities."}</p>
        </div>
        <button className="btn btn-outline-primary btn-sm" type="button" onClick={refresh} disabled={loading || (!location && !query.trim())}>
          <FiRefreshCw aria-hidden="true" /> Refresh
        </button>
      </div>

      {loading && <LoadingSpinner label="Finding nearby hospitals…" />}
      {!loading && (
        <div className="hospital-finder-layout">
          <section className="hospital-finder-list" aria-label="Hospital search results">
            {items.length ? items.map((hospital) => (
              <article className="surface-card hospital-finder-card" key={hospital.id}>
                <h4>{hospital.name}</h4>
                <p>{[hospital.address, hospital.city, hospital.district, hospital.state].filter(Boolean).join(", ") || "Address not listed"}</p>
                <div className="hospital-finder-tags">
                  <span>{hospital.distance_km} km away</span>
                  {hospital.hospital_type && <span>{hospital.hospital_type}</span>}
                  {hospital.emergency && <span>Emergency</span>}
                  {hospital.icu && <span>ICU</span>}
                  {hospital.blood_bank && <span>Blood bank</span>}
                  {hospital.ambulance && <span>Ambulance</span>}
                </div>
                <div className="hospital-finder-actions">
                  {hospital.phone && <a className="btn btn-outline-primary btn-sm" href={`tel:${hospital.phone}`}>Call {hospital.phone}</a>}
                  <a className="btn btn-link btn-sm" href={`https://www.google.com/maps/dir/?api=1&destination=${hospital.latitude},${hospital.longitude}`} target="_blank" rel="noreferrer">Directions</a>
                </div>
              </article>
            )) : (
              <div className="surface-card hospital-finder-empty">
                <FiMapPin aria-hidden="true" />
                <strong>No facilities to display</strong>
                <span>Search for a city or district, or allow location access.</span>
              </div>
            )}
          </section>
          <section className="surface-card hospital-finder-map" aria-label="Hospital locations map">
            <div className="surface-heading">
              <div><h3>Facility map</h3><p>{items.length} results</p></div>
            </div>
            <MapContainer center={center} zoom={location ? 11 : 5} scrollWheelZoom={false} className="hospital-leaflet-map">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {items.map((hospital) => (
                <CircleMarker
                  key={hospital.id}
                  center={[hospital.latitude, hospital.longitude]}
                  radius={8}
                  pathOptions={{ color: "#fff", weight: 2, fillColor: "#167b73", fillOpacity: 0.9 }}
                >
                  <Popup>
                    <strong>{hospital.name}</strong>
                    <br />
                    {hospital.distance_km} km away
                    {hospital.phone && <><br /><a href={`tel:${hospital.phone}`}>{hospital.phone}</a></>}
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </section>
        </div>
      )}
      <p className="hospital-finder-disclaimer">Facility details and listed services may be incomplete or out of date. Confirm availability directly with the hospital. For emergencies in India, call 112 or 108.</p>
    </main>
  );
}
