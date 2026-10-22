import { FiSearch } from "react-icons/fi";

export default function HospitalSearch({ value, onChange, onSearch, busy }) {
  return (
    <form className="hospital-search" onSubmit={(event) => { event.preventDefault(); onSearch(); }}>
      <label className="visually-hidden" htmlFor="hospital-search-input">Hospital, city, district or PIN code</label>
      <FiSearch aria-hidden="true" />
      <input id="hospital-search-input" className="form-control" value={value} onChange={(event) => onChange(event.target.value)} maxLength={200} placeholder="Search hospital, city, district or PIN code" />
      <button type="submit" className="btn btn-primary" disabled={busy || value.trim().length < 2}>{busy ? "Searching…" : "Search"}</button>
    </form>
  );
}
