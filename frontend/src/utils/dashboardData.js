import {
  FiActivity,
  FiCloud,
  FiDroplet,
  FiMap,
  FiMic,
  FiShield,
  FiThermometer,
  FiWind
} from "react-icons/fi";

export const climateFactors = [
  { title: "Temperature", description: "Warm conditions can accelerate mosquito development and shorten the virus incubation period.", importance: "A sustained rise can increase transmission potential.", icon: FiThermometer, color: "coral" },
  { title: "Humidity", description: "Moist air helps adult mosquitoes survive for longer and remain active.", importance: "High humidity supports longer mosquito survival.", icon: FiDroplet, color: "blue" },
  { title: "Rainfall", description: "Rain can create small pools of standing water where Aedes mosquitoes lay eggs.", importance: "Recent rain can increase nearby breeding sites.", icon: FiCloud, color: "teal" },
  { title: "Wind speed", description: "Wind influences how far mosquitoes can travel and how actively they feed.", importance: "Calm periods can support more mosquito activity.", icon: FiWind, color: "violet" },
  { title: "Air pressure", description: "Pressure is considered alongside weather history to identify changing local conditions.", importance: "A supporting signal in a broader climate picture.", icon: FiActivity, color: "amber" }
];

export const productFeatures = [
  { title: "Real-time weather", description: "Read current conditions and forecasts from connected weather services.", icon: FiCloud, color: "blue", href: "/weather" },
  { title: "Climate risk assessment", description: "Classify annual climate summaries with a trained three-network ensemble; outputs are research-only.", icon: FiActivity, color: "teal", href: "/prediction" },
  { title: "District weather map", description: "Explore Karnataka locations and their connected weather observations.", icon: FiMap, color: "coral", href: "/risk-map" },
  { title: "Climate reports", description: "Review weather observations saved by the connected service.", icon: FiShield, color: "violet", href: "/reports" },
  { title: "QR-ready profile", description: "Keep essential profile details available in one place.", icon: FiActivity, color: "amber", href: "/profile" },
  { title: "Voice climate input", description: "Dictate labelled climate values into the climate risk assessment form where browser speech recognition is supported.", icon: FiMic, color: "blue", href: "/prediction" },
  { title: "Forecast history", description: "Review saved forecasts, risk assessments, and recent activity.", icon: FiActivity, color: "teal", href: "/history" },
  { title: "Admin workspace", description: "A role-restricted UI for future project administration.", icon: FiShield, color: "coral", href: "/admin/dashboard" }
];

export const faqs = [
  { question: "What is dengue fever?", answer: "Dengue is a viral infection transmitted to people through the bites of infected Aedes mosquitoes. This project shares general information and is not a diagnostic service." },
  { question: "How is dengue transmitted?", answer: "Dengue viruses are mainly spread through the bite of infected Aedes aegypti mosquitoes. The disease does not usually spread directly from person to person." },
  { question: "What symptoms should I look for?", answer: "Common symptoms include high fever, headache, pain behind the eyes, muscle and joint pain, nausea, rash, and fatigue. Seek medical advice for concerns." },
  { question: "What are the warning signs of severe dengue?", answer: "Severe abdominal pain, persistent vomiting, bleeding, rapid breathing, unusual tiredness, or restlessness need urgent medical attention." },
  { question: "Can I use this project to diagnose dengue?", answer: "No. The climate-based model provides an experimental annual risk classification, not a diagnosis or an official outbreak forecast. Seek advice from a qualified healthcare professional." },
  { question: "What climate conditions are considered?", answer: "The model uses annual temperature, humidity, rainfall, wind, surface pressure, solar radiation, year, and State/UT. Historical case counts provide training labels, not request-time inputs." },
  { question: "How can I reduce mosquito breeding?", answer: "Empty, cover, or clean containers that collect water regularly. Follow local public-health guidance on mosquito control." },
  { question: "What should I do if I feel unwell?", answer: "Contact a qualified healthcare professional. If warning signs appear or symptoms worsen, seek urgent care rather than relying on an online forecast." },
  { question: "Does the application provide a dengue forecast?", answer: "It provides a separate historical case-trend projection and an experimental annual climate-based risk classification. Neither is an official surveillance forecast or medical advice." },
  { question: "Does the application store medical records?", answer: "This application does not provide medical-record storage. Weather requests may be saved as climate observations by the backend." }
];
