import { CircleMarker, Popup } from "react-leaflet";
import DistrictPopup from "./DistrictPopup.jsx";
import { getRiskColor } from "./riskColors.js";

export default function RiskMarker({ district, selected, onSelect }) {
  const color = getRiskColor(district.risk);

  return (
    <CircleMarker
      center={[district.latitude, district.longitude]}
      radius={selected ? 10 : 8}
      pathOptions={{
        color: "#ffffff",
        weight: selected ? 3 : 2,
        fillColor: color,
        fillOpacity: 0.92
      }}
      eventHandlers={{ click: () => onSelect(district) }}
    >
      <Popup>
        <DistrictPopup district={district} />
      </Popup>
    </CircleMarker>
  );
}
