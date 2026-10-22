import { FiCheckCircle } from "react-icons/fi";

const recommendations = [
  "Remove stagnant water around homes and workplaces.",
  "Wear full-sleeved clothing and use mosquito repellent.",
  "Keep water containers covered and clean them regularly.",
  "Seek medical care promptly if dengue symptoms appear."
];

export default function RecommendationCard() {
  return (
    <section className="weather-recommendations">
      <div className="weather-section-heading">
        <div><h2>Prevention recommendations</h2><p>Practical steps to reduce mosquito breeding and bites.</p></div>
      </div>
      <ul>
        {recommendations.map((recommendation) => (
          <li key={recommendation}><FiCheckCircle aria-hidden="true" /><span>{recommendation}</span></li>
        ))}
      </ul>
    </section>
  );
}
