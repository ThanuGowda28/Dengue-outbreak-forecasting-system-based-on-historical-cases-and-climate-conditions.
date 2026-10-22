import { useEffect } from "react";
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import { divIcon } from "leaflet";

const currentLocationIcon = divIcon({
  className: "hospital-current-location-icon",
  html: '<span aria-label="Your location"></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

function Recenter({ center }) {
  const map = useMap();
  useEffect(() => { map.setView(center, Math.max(map.getZoom(), 12)); }, [center, map]);
  return null;
}

export default function HospitalMap({ center, hospitals, onSelect }) {
  return (
    <div className="hospital-map">
      <MapContainer center={center} zoom={12} scrollWheelZoom>
        <Recenter center={center} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <CircleMarker center={center} radius={8} pathOptions={{ color: "#1576c5", fillColor: "#318fe0", fillOpacity: 0.9 }}>
          <Popup>Your location</Popup>
        </CircleMarker>
        {hospitals.map((hospital) => (
          <Marker key={hospital.id} position={[hospital.latitude, hospital.longitude]}>
            <Popup>
              <div className="hospital-map-popup">
                <strong>{hospital.name}</strong>
                <span>{hospital.hospital_type || "Medical facility"}</span>
                {hospital.distance_km != null && <span>{hospital.distance_km} km away</span>}
                <button type="button" className="btn btn-link btn-sm p-0" onClick={() => onSelect(hospital)}>View details</button>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
