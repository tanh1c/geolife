import { useEffect } from 'react';
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet';
import { latLngBounds } from 'leaflet';
import 'leaflet/dist/leaflet.css';

type Stay = { index: number; latitude: number; longitude: number; label: 'HOME' | 'OFFICE' | 'STOP' };

function FitStays({ stops }: { stops: Stay[] }) {
  const map = useMap();
  useEffect(() => {
    if (stops.length) map.fitBounds(latLngBounds(stops.map((stop) => [stop.latitude, stop.longitude])), { padding: [22, 22], maxZoom: 14 });
  }, [map, stops]);
  return null;
}

export function ResearchStayMap({ stops }: { stops: Stay[] }) {
  if (!stops.length) return <p role="status">Profile này chưa có điểm dừng để hiển thị.</p>;
  return (
    <div role="region" aria-label="Bản đồ điểm dừng GeoLife lịch sử" className="h-64 w-full overflow-hidden rounded-2xl border border-gray-200">
      <MapContainer center={[stops[0].latitude, stops[0].longitude]} zoom={12} scrollWheelZoom={false} className="h-full w-full">
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' referrerPolicy="strict-origin-when-cross-origin" url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <FitStays stops={stops} />
        {stops.map((stop) => (
          <CircleMarker key={stop.index} center={[stop.latitude, stop.longitude]} radius={stop.label === 'STOP' ? 4 : 8}
            pathOptions={{ color: stop.label === 'HOME' ? '#0e7490' : stop.label === 'OFFICE' ? '#b45309' : '#2563eb', fillOpacity: 0.8 }}>
            <Tooltip>{stop.label === 'STOP' ? 'Điểm dừng' : stop.label}</Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
