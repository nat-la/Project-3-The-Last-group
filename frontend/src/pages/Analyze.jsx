import { useEffect, useState } from "react";
import { api } from "../api";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import polyline from "@mapbox/polyline";
import { Polyline } from "react-leaflet";

export default function Analyze() {
  const [locations, setLocations] = useState([]);
  const [originId, setOriginId] = useState("");
  const [destId, setDestId] = useState("");
  const [routeRecs, setRouteRecs] = useState(null);
  const [error, setError] = useState("");
  const [stats, setStats] = useState(null);
  const [routeline, setRouteLine] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const locs = await api.listLocations();
        setLocations(locs);
        if (locs.length >= 2) {
          setOriginId(String(locs[0].id));
          setDestId(String(locs[1].id));
        }
      } catch (e) {
        setError(String(e.message || e));
      }
    })();
  }, []);

  async function generate() {
  setError("");
  try {
    const s = await api.routeStats(originId, destId);
    setStats(s);

    const poly = await api.routePolyline(originId, destId);
    const points = polyline.decode(poly.encoded_polyline);
    setRouteLine(points);
  } catch (e) {
    setError(String(e.message || e));
  }
}

  return (
    <div style={{ padding: 20 }}>
      <h1>Analyze</h1>
      {error && <div style={{ background: "#fee", padding: 10 }}>{error}</div>}

      <div style={{ display: "flex", gap: 20 }}>
        {/* Left panel */}
        <div style={{ width: 360, border: "1px solid #ddd", borderRadius: 10, padding: 12 }}>
          <h3>Route</h3>
          <label>Origin<br/>
            <select value={originId} onChange={(e)=>setOriginId(e.target.value)}>
              {locations.map((l)=> <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </label>
          <br/><br/>
          <label>Destination<br/>
            <select value={destId} onChange={(e)=>setDestId(e.target.value)}>
              {locations.map((l)=> <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </label>
          <br/><br/>
          <button onClick={generate} style={{ width: "100%" }}>Generate Trend Insights</button>

          <div style={{ marginTop: 14 }}>
            <h3>Insights</h3>
            <div style={{ marginTop: 14 }}>
            <h3>Insights</h3>
            {!stats ? (
                <p>Click “Generate Trend Insights”.</p>
            ) : stats.count === 0 ? (
                <p>No commutes found for this route yet.</p>
            ) : (
                <div style={{ border: "1px solid #ddd", borderRadius: 10, padding: 12 }}>
                <div><b>Samples:</b> {stats.count}</div>
                <div><b>Avg Est:</b> {stats.avg_estimated_minutes} min</div>
                <div><b>Avg Actual:</b> {stats.avg_actual_minutes} min</div>
                <div><b>% Worse:</b> {stats.percent_worse_than_estimated}%</div>
                </div>
            )}
            </div>

          </div>
        </div>

        <div style={{ flex: 1, border: "1px solid #ddd", borderRadius: 10, padding: 12 }}>
        <h3>Map</h3>

        <MapContainer
          center={[47.6062, -122.3321]}
          zoom={10}
          style={{ height: 520, width: "100%", borderRadius: 10 }}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {routeline && (
            <Polyline positions={routeline} color="blue" weight={4} />
          )}
          <Marker position={[47.6062, -122.3321]}>
            <Popup>Origin (placeholder)</Popup>
          </Marker>
          <Marker position={[47.55, -122.30]}>
            <Popup>Destination (placeholder)</Popup>
          </Marker>
        </MapContainer>

        <p style={{ marginTop: 10, opacity: 0.7 }}>
          * Route and stats are based on sample commute data and are for demonstration purposes only.
        </p>
      </div>

      </div>
    </div>
  );
}
