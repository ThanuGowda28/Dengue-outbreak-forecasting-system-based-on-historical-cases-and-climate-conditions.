import { FiAlertCircle } from "react-icons/fi";
import { getRiskColor } from "./riskColors.js";

export default function DistrictPopup({ district }) {
  return (
    <div className="district-risk-popup">
      <div className="district-risk-popup-heading">
        <strong>{district.district}</strong>
        <span style={{ color: getRiskColor(district.risk) }}>{district.risk} risk</span>
      </div>
      <dl>
        <div><dt>State</dt><dd>{district.state}</dd></div>
        <div><dt>Temperature</dt><dd>{district.temperature}°C</dd></div>
        <div><dt>Humidity</dt><dd>{district.humidity}%</dd></div>
        <div><dt>Rainfall (past 12 months)</dt><dd>{district.rainfall} mm</dd></div>
        <div><dt>Estimated risk score</dt><dd>{district.prediction}%</dd></div>
        <div><dt>Last updated</dt><dd>{district.last_updated ? new Date(district.last_updated).toLocaleString() : "—"}</dd></div>
      </dl>
      <div className="district-risk-recommendation">
        <FiAlertCircle aria-hidden="true" />
        <div>
          <strong>Recommended action</strong>
          <ul>
            {district.recommendations.map((recommendation) => (
              <li key={recommendation}>{recommendation}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
