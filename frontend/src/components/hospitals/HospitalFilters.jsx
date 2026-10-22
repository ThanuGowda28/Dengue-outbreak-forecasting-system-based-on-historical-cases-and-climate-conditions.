export default function HospitalFilters({ values, onChange }) {
  function update(key, value) {
    onChange({ ...values, [key]: value });
  }
  return (
    <section className="hospital-filters surface-card" aria-label="Hospital filters">
      <label>Within
        <select className="form-select" value={values.distance_km} onChange={(event) => update("distance_km", event.target.value)}>
          {[5, 10, 25, 50, 100].map((distance) => <option key={distance} value={distance}>{distance} km</option>)}
        </select>
      </label>
      <label>Facility
        <select className="form-select" value={values.type} onChange={(event) => update("type", event.target.value)}>
          <option value="">All types</option><option value="government">Government</option><option value="private">Private</option>
        </select>
      </label>
      <label>Minimum rating
        <select className="form-select" value={values.min_rating} onChange={(event) => update("min_rating", event.target.value)}>
          <option value="">Any rating</option>{[3, 3.5, 4, 4.5].map((rating) => <option key={rating} value={rating}>{rating}+ stars</option>)}
        </select>
      </label>
      <div className="hospital-filter-checks">
        {[
          ["open_24x7", "24×7"],
          ["emergency", "Emergency"],
          ["icu", "ICU"],
          ["blood_bank", "Blood bank"],
        ].map(([key, label]) => (
          <label className="form-check" key={key}>
            <input className="form-check-input" type="checkbox" checked={values[key] === "true"} onChange={(event) => update(key, event.target.checked ? "true" : "")} />
            <span>{label}</span>
          </label>
        ))}
      </div>
    </section>
  );
}
