import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FiActivity,
  FiArrowDown,
  FiArrowUpRight,
  FiBookOpen,
  FiCloud,
  FiDroplet,
  FiHeart,
  FiMapPin,
  FiShield,
  FiThermometer,
  FiWind
} from "react-icons/fi";
import { ContactForm, EmptyState, FAQCard, FeatureCard, InfoCard } from "../components/DashboardComponents.jsx";
import { DengueLineChart } from "../components/TrendCharts.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { getStatistics } from "../services/dashboardService.js";
import { climateFactors, faqs, productFeatures } from "../utils/dashboardData.js";

const timeline = [
  ["01", "Climate data", "Historical weather and case observations"],
  ["02", "Data cleaning", "Quality checks and feature preparation"],
  ["03", "Ensemble network", "Combine learned patterns from climate signals"],
  ["04", "Prediction", "Estimate a community-level outlook"],
  ["05", "Dashboard", "Present context, trends, and risk indicators"]
];

export default function HomePage() {
  const { isAuthenticated } = useAuth();
  const [statistics, setStatistics] = useState(null);
  const [statisticsError, setStatisticsError] = useState("");
  const [statisticsLoading, setStatisticsLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return undefined;
    let active = true;
    setStatisticsLoading(true);
    getStatistics()
      .then((data) => { if (active) setStatistics(data); })
      .catch((error) => {
        if (active) setStatisticsError(error.response?.data?.message || "Climate statistics could not be loaded.");
      })
      .finally(() => { if (active) setStatisticsLoading(false); });
    return () => { active = false; };
  }, [isAuthenticated]);

  const reportStatistics = statistics?.statistics || {};
  const monthlyWeather = Array.isArray(reportStatistics.monthly_weather) ? reportStatistics.monthly_weather : [];
  const weatherTrend = Array.isArray(reportStatistics.temperature_trend) ? reportStatistics.temperature_trend : [];
  const humidityTrend = Array.isArray(reportStatistics.humidity_trend) ? reportStatistics.humidity_trend : [];
  const rainfallTrend = Array.isArray(reportStatistics.rainfall_trend) ? reportStatistics.rainfall_trend : [];
  const labelsFor = (rows) => rows.map((row) => row.month || new Date(`${row.weather_date}T12:00:00`).toLocaleDateString(undefined, { month: "short", year: "2-digit" }));

  return (
    <main className="landing-page">
      <section className="landing-hero">
        <div className="container landing-hero-grid">
          <div className="landing-hero-copy">
            <span className="landing-badge"><span className="live-dot" /> CLIMATE-AWARE HEALTH INSIGHTS</span>
            <h1>AI Powered Dengue Outbreak <span>Forecasting</span></h1>
            <p>Explore how historical dengue cases and climate signals can come together to support earlier awareness and smarter public-health planning.</p>
            <div className="d-flex flex-wrap gap-3"><Link className="btn btn-primary btn-lg" to={isAuthenticated ? "/dashboard" : "/register"}>{isAuthenticated ? "Open dashboard" : "Get started"} <FiArrowUpRight className="ms-2" /></Link><a className="btn btn-outline-light btn-lg" href="#about">Learn more</a></div>
            <div className="landing-proof"><span><FiShield /> Research-led approach</span><span><FiActivity /> Climate + case insights</span></div>
          </div>
          <div className="medical-illustration" aria-label="Decorative illustration of a climate and health monitoring dashboard">
            <div className="illustration-orbit illustration-orbit-one" /><div className="illustration-orbit illustration-orbit-two" />
            <div className="illustration-glow" />
            <div className="illustration-core"><FiActivity /><small>COMMUNITY HEALTH</small><strong>Early insight</strong></div>
            <div className="floating-climate"><FiCloud /><span><small>CLIMATE SIGNALS</small><strong>5 factors monitored</strong></span></div>
            <div className="floating-risk"><span className="risk-spark"><FiHeart /></span><span><small>LOCAL OUTLOOK</small><strong>Risk awareness</strong></span><span className="risk-chip">LIVE UI</span></div>
            <span className="illustration-point illustration-point-a" /><span className="illustration-point illustration-point-b" /><span className="illustration-point illustration-point-c" />
          </div>
          <a className="hero-scroll" href="#about" aria-label="Scroll to about section"><FiArrowDown /></a>
        </div>
      </section>

      <section className="landing-section landing-about" id="about">
        <div className="container">
          <div className="section-title-block"><span className="page-overline">ABOUT THE PROJECT</span><h2>Turning climate context into clearer insight.</h2><p>A final-year engineering project exploring ensemble neural networks for dengue outbreak forecasting.</p></div>
          <div className="row g-3">
            <div className="col-md-6 col-xl-3"><InfoCard title="Purpose" description="Connect historical case data with climate patterns in a clear, accessible workspace." icon={FiHeart} color="teal" /></div>
            <div className="col-md-6 col-xl-3"><InfoCard title="Objectives" description="Explore model inputs, prepare data, and evaluate an ensemble neural-network approach." icon={FiActivity} color="blue" /></div>
            <div className="col-md-6 col-xl-3"><InfoCard title="Technology" description="React, Flask, MySQL, TensorFlow/Keras, and scikit-learn." icon={FiBookOpen} color="violet" /></div>
            <div className="col-md-6 col-xl-3"><InfoCard title="Benefits" description="Explore regional weather context through provider-backed observations and reports." icon={FiShield} color="amber" /></div>
          </div>
          <Link className="section-inline-link" to="/about">Explore the project <FiArrowUpRight /></Link>
        </div>
      </section>

      <section className="landing-section disease-section">
        <div className="container disease-grid">
          <div><span className="page-overline">DENGUE INFORMATION</span><h2>Knowledge helps communities take action.</h2><p>Dengue is a mosquito-borne viral infection. Recognizing symptoms, reducing mosquito breeding sites, and following local health advice matter.</p><Link to="/symptoms" className="btn btn-outline-primary">Learn about symptoms</Link></div>
          <div className="disease-facts">
            <article><span className="fact-icon fact-coral"><FiThermometer /></span><span><strong>Symptoms</strong><small>Fever, headache, body aches, rash, nausea, and fatigue may occur.</small></span></article>
            <article><span className="fact-icon fact-blue"><FiActivity /></span><span><strong>Transmission</strong><small>Primarily spread through the bite of an infected Aedes mosquito.</small></span></article>
            <article><span className="fact-icon fact-amber"><FiDroplet /></span><span><strong>Risk factors</strong><small>Standing water can provide breeding sites; local conditions vary.</small></span></article>
            <article><span className="fact-icon fact-teal"><FiHeart /></span><span><strong>Treatment</strong><small>Seek advice from a qualified healthcare professional for symptoms.</small></span></article>
          </div>
        </div>
      </section>

      <section className="landing-section" id="climate">
        <div className="container">
          <div className="section-title-block"><span className="page-overline">CLIMATE FACTORS</span><h2>Weather patterns are part of the picture.</h2><p>Climate variables can influence mosquito habitats and are considered alongside historical case observations.</p></div>
          <div className="row g-3">{climateFactors.map((factor) => <div className="col-md-6 col-xl" key={factor.title}><InfoCard {...factor} /></div>)}</div>
        </div>
      </section>

      <section className="landing-section timeline-section">
        <div className="container"><div className="section-title-block text-center mx-auto"><span className="page-overline">HOW PREDICTION WORKS</span><h2>From climate signals to a useful view.</h2><p>An overview of the research pipeline — not a live production model.</p></div>
          <div className="prediction-timeline">{timeline.map(([number, title, description], index) => <article className="timeline-step" key={number}><span className="timeline-number">{number}</span><span className="timeline-connector" /><h3>{title}</h3><p>{description}</p>{index < timeline.length - 1 && <FiArrowUpRight className="timeline-arrow" />}</article>)}</div>
        </div>
      </section>

      <section className="landing-section landing-features">
        <div className="container"><div className="section-title-block"><span className="page-overline">EXPLORE THE PLATFORM</span><h2>Useful tools, designed around people.</h2><p>Explore provider-backed weather alongside project modules that are still in development.</p></div>
          <div className="row g-3">{productFeatures.map((feature) => <div className="col-sm-6 col-xl-3" key={feature.title}><FeatureCard {...feature} /></div>)}</div>
        </div>
      </section>

      <section className="landing-section statistics-section">
        <div className="container"><div className="section-title-block"><span className="page-overline">CLIMATE REPORTS</span><h2>Observed weather, in context.</h2><p>Charts use stored provider observations. This page does not present dengue case counts or model-evaluation metrics.</p></div>
          {statisticsError && <div className="alert alert-warning" role="alert">{statisticsError}</div>}
          {statisticsLoading && <div className="weather-loading"><span className="spinner-border spinner-border-sm text-primary" role="status" />Loading climate reports…</div>}
          {!isAuthenticated && <div className="surface-card mb-3"><EmptyState title="Sign in to view climate reports" description="Stored observations are available in the authenticated reports workspace." action={<Link className="btn btn-outline-primary btn-sm mt-3" to="/login">Sign in</Link>} /></div>}
          <div className="row g-3">
            {isAuthenticated && <div className="col-xl-6"><section className="surface-card landing-chart-card"><h3>Monthly average temperature</h3><p>Recorded climate observations</p><div className="landing-chart">{monthlyWeather.length ? <DengueLineChart labels={labelsFor(monthlyWeather)} data={monthlyWeather.map((row) => row.temperature)} color="#1976d2" fill label="Temperature (°C)" /> : <EmptyState title="No monthly observations" description="No stored weather is available yet." />}</div></section></div>}
            {isAuthenticated && <div className="col-xl-6"><section className="surface-card landing-chart-card"><h3>Temperature trend</h3><p>Daily observations returned by the reports API</p><div className="landing-chart">{weatherTrend.length ? <DengueLineChart labels={labelsFor(weatherTrend)} data={weatherTrend.map((row) => row.temperature)} color="#1976d2" fill label="Temperature (°C)" /> : <EmptyState title="No temperature trend" description="Stored observations will appear here when available." />}</div></section></div>}
            {isAuthenticated && <div className="col-xl-6"><section className="surface-card landing-chart-card"><h3>Humidity trend</h3><p>Daily relative humidity observations</p><div className="landing-chart">{humidityTrend.length ? <DengueLineChart labels={labelsFor(humidityTrend)} data={humidityTrend.map((row) => row.humidity)} color="#43a047" fill label="Humidity (%)" /> : <EmptyState title="No humidity trend" description="Stored observations will appear here when available." />}</div></section></div>}
            {isAuthenticated && <div className="col-xl-6"><section className="surface-card landing-chart-card"><h3>Rainfall trend</h3><p>Daily recorded rainfall observations</p><div className="landing-chart">{rainfallTrend.length ? <DengueLineChart labels={labelsFor(rainfallTrend)} data={rainfallTrend.map((row) => row.rainfall)} color="#009688" fill label="Rainfall (mm)" /> : <EmptyState title="No rainfall trend" description="Stored observations will appear here when available." />}</div></section></div>}
          </div>
        </div>
      </section>

      <section className="landing-section faq-section" id="faq">
        <div className="container faq-grid"><div><span className="page-overline">GOOD TO KNOW</span><h2>Questions, answered clearly.</h2><p>Understand dengue, climate observations, and what this project does — and does not — do.</p><Link to="/faq" className="section-inline-link">See all FAQs <FiArrowUpRight /></Link></div><FAQCard items={faqs.slice(0, 5)} /></div>
      </section>

      <section className="landing-section landing-contact" id="contact">
        <div className="container contact-home-grid"><div><span className="page-overline">CONTACT</span><h2>Let’s make this project better.</h2><p>Questions or feedback about the academic project? Leave a note in this demo form.</p><div className="contact-summary"><span><FiShield /> Project demonstration · No live health data</span><span><FiHeart /> Emergency support in India: call 112.</span></div></div><div className="surface-card contact-card"><ContactForm /></div></div>
      </section>
    </main>
  );
}
