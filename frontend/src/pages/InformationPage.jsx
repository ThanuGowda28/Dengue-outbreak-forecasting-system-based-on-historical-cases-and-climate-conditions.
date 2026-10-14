import { Link, useParams } from "react-router-dom";
import {
  FiActivity,
  FiAlertTriangle,
  FiBookOpen,
  FiCheckCircle,
  FiDroplet,
  FiHeart,
  FiShield,
  FiTarget,
  FiThermometer,
  FiWind
} from "react-icons/fi";
import { InfoCard } from "../components/DashboardComponents.jsx";
import { climateFactors } from "../utils/dashboardData.js";

const pageContent = {
  about: {
    eyebrow: "ABOUT THE PROJECT",
    title: "A clearer view of dengue risk.",
    description: "A final-year engineering project exploring how historical dengue observations and climate conditions could support community-level outbreak forecasting.",
    cards: [
      ["Purpose", "Make climate and historical-case context easier to understand through a clear, accessible interface.", FiHeart],
      ["Objectives", "Explore an ensemble neural-network approach and present its assumptions, inputs, and evaluation transparently.", FiTarget],
      ["Technology", "React, Flask, MySQL, TensorFlow/Keras, scikit-learn, and interpretable visual summaries.", FiActivity],
      ["Potential benefit", "Support awareness and research by making modeled community trends easier to explore.", FiShield]
    ]
  },
  symptoms: {
    eyebrow: "DENGUE INFORMATION",
    title: "Recognize symptoms. Seek care.",
    description: "Dengue symptoms vary. This educational summary is not a diagnosis; contact a qualified health professional for personal advice.",
    cards: [
      ["What is dengue?", "Dengue is a viral infection transmitted to people through the bites of infected Aedes mosquitoes.", FiBookOpen],
      ["Cause", "Dengue is caused by dengue viruses. A person is typically infected after the bite of an infected mosquito.", FiActivity],
      ["Transmission", "Aedes mosquitoes can spread dengue viruses between people. Dengue is not usually spread directly person to person.", FiWind],
      ["Common symptoms", "High fever, headache, pain behind the eyes, muscle or joint aches, nausea, rash, and fatigue can occur.", FiThermometer],
      ["Risk factors", "Exposure to infected mosquitoes and local transmission conditions can affect a person's risk.", FiDroplet],
      ["Urgent warning signs", "Severe abdominal pain, persistent vomiting, bleeding, rapid breathing, unusual tiredness, or restlessness need urgent care.", FiAlertTriangle],
      ["Treatment", "There is no specific self-care substitute for clinical evaluation. A healthcare professional can advise on appropriate care.", FiHeart]
    ]
  },
  prevention: {
    eyebrow: "PREVENTION",
    title: "Small steps can reduce breeding sites.",
    description: "Aedes mosquitoes can breed in small containers of standing water. Follow local public-health guidance.",
    cards: [
      ["Empty standing water", "Regularly empty and clean containers that can collect water, including trays, pots, and buckets.", FiDroplet],
      ["Cover water storage", "Keep water containers tightly covered and check them routinely.", FiShield],
      ["Protect yourself", "Use locally recommended mosquito protection and seek advice from a healthcare professional.", FiCheckCircle],
      ["Keep community informed", "Share official local public-health notices and support neighborhood clean-up efforts.", FiHeart]
    ]
  },
  "privacy-policy": {
    eyebrow: "PROJECT INFORMATION",
    title: "Privacy notice",
    description: "This project connects to weather services and can store successful weather observations in its backend.",
    cards: [
      ["Weather requests", "Weather observations and location coordinates may be recorded by the backend to support climate history and reports.", FiBookOpen],
      ["Account area", "Account information is handled by the authentication module. Do not submit sensitive personal or medical information.", FiShield],
      ["Deployment", "Operators should publish applicable data-retention, consent, access-control, and user-rights policies before public deployment.", FiCheckCircle]
    ]
  },
  "terms-of-use": {
    eyebrow: "PROJECT INFORMATION",
    title: "Terms of use",
    description: "Use this student project interface for demonstration and educational exploration only.",
    cards: [
      ["Not medical advice", "The application is not a medical device, diagnostic tool, or substitute for professional care.", FiHeart],
      ["Forecasts unavailable", "The prediction page does not currently produce dengue forecasts. Weather conditions are not dengue risk scores.", FiActivity],
      ["Use official guidance", "For health decisions, follow current instructions from qualified healthcare providers and public-health authorities.", FiShield]
    ]
  }
};

export default function InformationPage() {
  const { slug = "about" } = useParams();
  const content = pageContent[slug] || pageContent.about;
  const climatePage = slug === "climate";
  const cards = climatePage
    ? climateFactors.map(({ title, description, importance, icon, color }) => [title, description, icon, importance, color])
    : content.cards.map(([title, description, icon], index) => [title, description, icon, null, ["teal", "blue", "coral", "violet"][index % 4]]);

  return (
    <main className="info-page">
      <section className="info-page-hero"><div className="container"><span className="page-overline">{climatePage ? "CLIMATE & TRANSMISSION" : content.eyebrow}</span><h1>{climatePage ? "Climate shapes mosquito habitats." : content.title}</h1><p>{climatePage ? "Weather variables can influence mosquito breeding and survival. Our project explores these as model inputs alongside historical case records." : content.description}</p></div></section>
      <section className="container py-5"><div className="row g-3">{cards.map(([title, description, Icon, importance, color]) => <div className="col-md-6 col-xl-4" key={title}><InfoCard title={title} description={description} icon={Icon} importance={importance} color={color} /></div>)}</div>
        <div className="info-disclaimer"><FiWind /><p>Information is general and educational. It does not diagnose, treat, or prevent disease. Seek advice from a qualified healthcare professional.</p></div>
        <Link className="btn btn-primary mt-3" to="/prevention">Explore prevention guidance</Link>
      </section>
    </main>
  );
}
