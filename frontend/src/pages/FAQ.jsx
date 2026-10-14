import { FAQCard } from "../components/DashboardComponents.jsx";
import { faqs } from "../utils/dashboardData.js";

export default function FAQ() {
  return (
    <main className="info-page">
      <section className="info-page-hero"><div className="container"><span className="page-overline">HELP & INFORMATION</span><h1>Frequently asked questions</h1><p>Learn about dengue, climate observations, and what this project can and cannot tell you.</p></div></section>
      <section className="container faq-page-content"><FAQCard items={faqs} /><p className="demo-disclaimer">If you are concerned about symptoms, contact a qualified healthcare professional. Forecasts are not diagnoses.</p></section>
    </main>
  );
}
