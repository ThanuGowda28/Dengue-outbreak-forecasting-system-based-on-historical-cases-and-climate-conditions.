import { FiClock, FiDroplet, FiExternalLink, FiMapPin, FiPhone, FiShield } from "react-icons/fi";

export default function HospitalCard({ hospital, onSelect }) {
  const directions = `https://www.google.com/maps/dir/?api=1&destination=${hospital.latitude},${hospital.longitude}`;
  return (
    <article className="hospital-card">
      <div className="hospital-card-heading">
        <span className="hospital-icon"><FiShield aria-hidden="true" /></span>
        <div>
          <h3>{hospital.name}</h3>
          <span className="hospital-type">{hospital.hospital_type || "Medical facility"}</span>
        </div>
        {hospital.emergency && <span className="hospital-emergency-badge">Emergency</span>}
      </div>
      <p className="hospital-address"><FiMapPin aria-hidden="true" />{hospital.address || [hospital.city, hospital.district, hospital.pincode].filter(Boolean).join(", ") || "Address not listed"}</p>
      <div className="hospital-facts">
        {hospital.distance_km != null && <span className="hospital-distance">{hospital.distance_km} km away</span>}
        {hospital.rating != null && <span>★ {Number(hospital.rating).toFixed(1)}</span>}
        {hospital.opening_hours && <span><FiClock aria-hidden="true" />{hospital.opening_hours}</span>}
      </div>
      <div className="hospital-service-tags" aria-label="Available services">
        {hospital.icu && <span>ICU</span>}
        {hospital.ambulance && <span>Ambulance</span>}
        {hospital.blood_bank && <span><FiDroplet aria-hidden="true" />Blood bank</span>}
        {!hospital.emergency && <span className="hospital-service-muted">Emergency not listed</span>}
      </div>
      <div className="hospital-actions">
        <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => onSelect?.(hospital)}>Details</button>
        <a className="btn btn-outline-primary btn-sm" href={directions} target="_blank" rel="noreferrer"><FiExternalLink aria-hidden="true" /> Directions</a>
        {hospital.phone && <a className="btn btn-primary btn-sm" href={`tel:${hospital.phone}`}><FiPhone aria-hidden="true" /> Call</a>}
      </div>
    </article>
  );
}
