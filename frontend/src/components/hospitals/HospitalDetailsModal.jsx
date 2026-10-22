import { FiDroplet, FiExternalLink, FiPhone, FiX } from "react-icons/fi";

export default function HospitalDetailsModal({ hospital, onClose }) {
  if (!hospital) return null;
  const directions = `https://www.google.com/maps/dir/?api=1&destination=${hospital.latitude},${hospital.longitude}`;
  return (
    <div className="hospital-modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="hospital-details-modal" role="dialog" aria-modal="true" aria-labelledby="hospital-modal-title">
        <button type="button" className="hospital-modal-close" onClick={onClose} aria-label="Close hospital details"><FiX /></button>
        <span className="page-overline">MEDICAL FACILITY</span>
        <h2 id="hospital-modal-title">{hospital.name}</h2>
        <p>{hospital.address || [hospital.city, hospital.district, hospital.pincode].filter(Boolean).join(", ") || "Address not listed"}</p>
        <dl className="hospital-details-list">
          <div><dt>Type</dt><dd>{hospital.hospital_type || "Not listed"}</dd></div>
          <div><dt>Distance</dt><dd>{hospital.distance_km == null ? "Not available" : `${hospital.distance_km} km`}</dd></div>
          <div><dt>Phone</dt><dd>{hospital.phone || "Not listed"}</dd></div>
          <div><dt>Working hours</dt><dd>{hospital.opening_hours || "Not listed"}</dd></div>
          <div><dt>Emergency</dt><dd>{hospital.emergency ? "Available" : "Not listed"}</dd></div>
          <div><dt>ICU</dt><dd>{hospital.icu ? "Available" : "Not listed"}</dd></div>
          <div><dt>Ambulance</dt><dd>{hospital.ambulance ? "Available" : "Not listed"}</dd></div>
          <div><dt>Blood bank</dt><dd>{hospital.blood_bank ? "Available" : "Not listed"}</dd></div>
          <div><dt>Rating</dt><dd>{hospital.rating == null ? "Not listed" : `${Number(hospital.rating).toFixed(1)} / 5`}</dd></div>
        </dl>
        <div className="hospital-actions">
          {hospital.phone && <a className="btn btn-primary" href={`tel:${hospital.phone}`}><FiPhone /> Call hospital</a>}
          {hospital.ambulance_phone && <a className="btn btn-danger" href={`tel:${hospital.ambulance_phone}`}><FiPhone /> Call ambulance</a>}
          {hospital.blood_bank && <span className="btn btn-outline-primary disabled"><FiDroplet /> Blood bank</span>}
          {hospital.website && <a className="btn btn-outline-primary" href={hospital.website} target="_blank" rel="noreferrer">Website <FiExternalLink /></a>}
          <a className="btn btn-outline-primary" href={directions} target="_blank" rel="noreferrer">Open in Google Maps <FiExternalLink /></a>
        </div>
      </section>
    </div>
  );
}
