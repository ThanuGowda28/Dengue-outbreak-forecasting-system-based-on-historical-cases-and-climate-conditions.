import { useEffect, useState } from "react";
import { FiCheck, FiSearch } from "react-icons/fi";
import { Link } from "react-router-dom";
import { normalizeRiskTone } from "../utils/risk.js";
import { submitContactMessage } from "../services/contactService.js";

export function DashboardCard({ label, value, change, icon, tone = "teal" }) {
  return (
    <article className="dashboard-stat">
      <div className="dashboard-stat-copy">
        <span>{label}</span>
        <strong>{value}</strong>
        {change && <small>{change}</small>}
      </div>
      <span className={`stat-icon tone-${tone}`} aria-hidden="true">{icon}</span>
    </article>
  );
}

export function ChartCard({ title, subtitle, children, className = "" }) {
  return (
    <section className={`surface-card chart-card ${className}`}>
      <div className="surface-heading">
        <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
      </div>
      <div className="chart-canvas">{children}</div>
    </section>
  );
}

export function WeatherCard({ day, icon, high, low, condition, rain, current = false }) {
  const Icon = icon;
  return (
    <article className={`weather-tile ${current ? "weather-tile-current" : ""}`}>
      <span className="weather-day">{day}</span>
      <Icon className="weather-tile-icon" aria-hidden="true" />
      <span className="weather-condition">{condition}</span>
      <strong>{high}° <span>{low}°</span></strong>
      {rain && <small><span aria-hidden="true">☂</span> {rain}</small>}
    </article>
  );
}

export function PredictionCard({ district, date, risk, confidence }) {
  return (
    <article className="prediction-row">
      <span className="prediction-avatar" aria-hidden="true">{district.slice(0, 1)}</span>
      <div className="prediction-place"><strong>{district}</strong><small>{date}</small></div>
      <RiskIndicator level={risk} />
      <span className="prediction-confidence">{confidence}</span>
    </article>
  );
}

export function FeatureCard({ icon: Icon, title, description, href = "/about", color = "teal" }) {
  return (
    <Link className="feature-card feature-card-link" to={href}>
      <span className={`feature-icon feature-icon-${color}`}><Icon aria-hidden="true" /></span>
      <h3>{title}</h3>
      <p>{description}</p>
      <span className="feature-arrow" aria-hidden="true">↗</span>
    </Link>
  );
}

export function InfoCard({ icon: Icon, title, description, importance, color = "teal" }) {
  return (
    <article className="info-card">
      <span className={`feature-icon feature-icon-${color}`}><Icon aria-hidden="true" /></span>
      <h3>{title}</h3>
      <p>{description}</p>
      {importance && <div className="info-card-importance"><strong>Why it matters</strong><span>{importance}</span></div>}
    </article>
  );
}

export function FAQCard({ items }) {
  return (
    <div className="faq-accordion">
      {items.map((item, index) => (
        <details className="faq-item" key={item.question} open={index === 0}>
          <summary><span className="faq-number">{String(index + 1).padStart(2, "0")}</span>{item.question}<span className="faq-toggle" aria-hidden="true" /></summary>
          <div className="faq-answer">{item.answer}</div>
        </details>
      ))}
    </div>
  );
}

export function RiskIndicator({ level }) {
  const label = level || "Low";
  return <span className={`risk-pill risk-${normalizeRiskTone(label)}`}>{label}</span>;
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="empty-state">
      {Icon && <span className="empty-state-icon"><Icon aria-hidden="true" /></span>}
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function SearchBar({ value, onChange, placeholder = "Search" }) {
  return (
    <label className="search-control">
      <FiSearch aria-hidden="true" />
      <span className="visually-hidden">{placeholder}</span>
      <input value={value} onChange={onChange} placeholder={placeholder} />
    </label>
  );
}

export function Pagination({ page, pageCount, onChange }) {
  if (pageCount < 2) return null;
  return (
    <nav aria-label="Pagination">
      <ul className="pagination pagination-sm mb-0">
        <li className={`page-item ${page <= 1 ? "disabled" : ""}`}>
          <button className="page-link" type="button" onClick={() => onChange(page - 1)} disabled={page <= 1}>Previous</button>
        </li>
        {Array.from({ length: pageCount }, (_, index) => index + 1).map((number) => (
          <li className={`page-item ${page === number ? "active" : ""}`} key={number}>
            <button className="page-link" type="button" onClick={() => onChange(number)} aria-current={page === number ? "page" : undefined}>{number}</button>
          </li>
        ))}
        <li className={`page-item ${page >= pageCount ? "disabled" : ""}`}>
          <button className="page-link" type="button" onClick={() => onChange(page + 1)} disabled={page >= pageCount}>Next</button>
        </li>
      </ul>
    </nav>
  );
}

export function Modal({ open, title, onClose, children }) {
  useEffect(() => {
    if (!open) return undefined;
    function closeOnEscape(event) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="modal-backdrop-custom" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="modal-card-custom" role="dialog" aria-modal="true" aria-labelledby="app-modal-title">
        <div className="surface-heading"><h2 id="app-modal-title">{title}</h2><button className="btn-close" type="button" onClick={onClose} aria-label="Close dialog" /></div>
        <div>{children}</div>
      </section>
    </div>
  );
}

export function ToastNotification({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="app-toast" role="status">
      <FiCheck aria-hidden="true" /><span>{message}</span>
      <button type="button" className="btn-close" aria-label="Dismiss notification" onClick={onDismiss} />
    </div>
  );
}

export function ContactForm() {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form));
    try {
      await submitContactMessage(payload);
      setSubmitted(true);
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Your message could not be sent. Please try again later.");
    } finally {
      setLoading(false);
    }
  }
  return submitted ? (
    <div className="alert alert-success" role="status">Thanks — your message has been sent to the project team.</div>
  ) : (
    <form className="contact-form" onSubmit={submit}>
      {error && <div className="alert alert-danger" role="alert">{error}</div>}
      <div className="row g-3">
        <div className="col-sm-6"><label className="form-label" htmlFor="contact-name">Name</label><input className="form-control" id="contact-name" name="name" autoComplete="name" required /></div>
        <div className="col-sm-6"><label className="form-label" htmlFor="contact-email">Email</label><input className="form-control" id="contact-email" name="email" type="email" autoComplete="email" required /></div>
        <div className="col-12"><label className="form-label" htmlFor="contact-topic">What would you like to share?</label><textarea className="form-control" id="contact-topic" name="message" rows="4" required /></div>
        <div className="col-12"><button className="btn btn-primary" type="submit" disabled={loading}>{loading ? "Sending…" : "Send message"}</button></div>
      </div>
    </form>
  );
}
