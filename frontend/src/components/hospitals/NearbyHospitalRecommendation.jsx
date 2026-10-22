import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FiAlertTriangle, FiMapPin, FiPhone } from "react-icons/fi";
import { getNearbyHospitals } from "../../services/hospitalService.js";

export default function NearbyHospitalRecommendation({ district, state }) {
  const [items, setItems] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const params = { distance_km: 25 };
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => {
          getNearbyHospitals({
            ...params,
            latitude: coords.latitude,
            longitude: coords.longitude,
          }).then((data) => {
            if (active) setItems((data.items || []).slice(0, 3));
          }).catch((error) => {
            if (active) setMessage(error.response?.data?.message || "Nearby facilities are unavailable.");
          }).finally(() => { if (active) setLoading(false); });
        },
        () => loadByProfile(),
        { timeout: 7000, maximumAge: 60000 },
      );
    } else {
      loadByProfile();
    }

    function loadByProfile() {
      const location = [district, state].filter(Boolean).join(", ");
      if (!location) {
        if (active) {
          setMessage("Allow location access or search for your district to find nearby care.");
          setLoading(false);
        }
        return;
      }
      getNearbyHospitals({ ...params, location })
        .then((data) => { if (active) setItems((data.items || []).slice(0, 3)); })
        .catch((error) => {
          if (active) setMessage(error.response?.data?.message || "Nearby facilities are unavailable.");
        })
        .finally(() => { if (active) setLoading(false); });
    }
    return () => { active = false; };
  }, [district, state]);

  return (
    <section className="hospital-recommendation" aria-live="polite">
      <div className="hospital-recommendation-heading"><FiAlertTriangle /><div><h3>Nearby Hospitals</h3><p>Consider contacting a medical professional. This model result is not a diagnosis.</p></div></div>
      {loading ? <p role="status">Finding nearby facilities…</p> : items.length ? (
        <ul>{items.map((hospital) => <li key={hospital.id}>
          <span><strong>{hospital.name}</strong><small><FiMapPin /> {hospital.distance_km} km · {hospital.hospital_type}</small></span>
          {hospital.phone && <a href={`tel:${hospital.phone}`} aria-label={`Call ${hospital.name}`}><FiPhone /> Call</a>}
        </li>)}</ul>
      ) : <p>{message || "No nearby facilities were found for the available location."}</p>}
      <Link className="btn btn-danger btn-sm" to={`/hospital-finder?location=${encodeURIComponent([district, state].filter(Boolean).join(", "))}`}>Find Nearby Hospitals</Link>
    </section>
  );
}
