import { FiClock, FiPhone } from "react-icons/fi";
import { ContactForm } from "../components/DashboardComponents.jsx";

export default function Contact() {
  return (
    <main className="info-page">
      <section className="info-page-hero"><div className="container"><span className="page-overline">GET IN TOUCH</span><h1>Contact the project team</h1><p>Share feedback about this academic project demonstration.</p></div></section>
      <section className="container py-5"><div className="row g-4">
        <div className="col-lg-7"><div className="surface-card contact-card"><h2>Send a message</h2><p className="text-secondary mb-4">Send a message to the project team.</p><ContactForm /></div></div>
        <div className="col-lg-5"><div className="surface-card contact-card"><h2>Health support</h2><p className="text-secondary">For medical advice, use local official healthcare services.</p><div className="contact-detail"><FiPhone /><span><strong>Emergency</strong><a href="tel:112">112 · India emergency response</a></span></div><div className="contact-detail"><FiPhone /><span><strong>Health advice</strong><a href="tel:104">104 · Karnataka health helpline</a><small>Confirm current availability with local authorities.</small></span></div><div className="contact-detail"><FiClock /><span><strong>Urgent symptoms</strong><span>Seek immediate medical attention.</span></span></div></div></div>
      </div></section>
    </main>
  );
}
