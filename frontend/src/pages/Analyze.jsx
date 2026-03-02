

import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import polyline from "@mapbox/polyline";
import { Alert, Field, PageHeader } from "../components/ui";

export default function Analyze() {
  const [locations, setLocations] = useState([]);
  const [originId, setOriginId] = useState("");
  const [destId, setDestId] = useState("");
  const [error, setError] = useState("");
  const [stats, setStats] = useState(null);
  const [routeLine, setRouteLine] = useState(null);
  const [loading, setLoading] = useState(false);
  const [routeInfo, setRouteInfo] = useState(null);
  const [byHour, setByHour] = useState([]);
  const [actualMinutes, setActualMinutes] = useState("");
  const [logStatus, setLogStatus] = useState("");

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
        setError(String(e?.message || e));
      }
    })();
  }, []);

  const origin = useMemo(
    () => locations.find((l) => String(l.id) === String(originId)) || null,
    [locations, originId]
  );
  const dest = useMemo(
    () => locations.find((l) => String(l.id) === String(destId)) || null,
    [locations, destId]
  );

  const bestWorst = useMemo(() => {
  if (!byHour || byHour.length === 0) return null;

  // sort by percent_worse_than_estimated ascending => best
  const sorted = [...byHour].sort(
    (a, b) => a.percent_worse_than_estimated - b.percent_worse_than_estimated
  );

  const best = sorted.slice(0, 3);
  const worst = sorted.slice(-3).reverse(); // top 3 worst

  return { best, worst };
  }, [byHour]);

  const historicalNow = useMemo(() => {
  if (!byHour || byHour.length === 0) return null;

  const currentHour = new Date().getHours();

  const match = byHour.find((h) => Number(h.hour) === Number(currentHour));
  if (!match) return { currentHour, match: null };

  return { currentHour, match };
  }, [byHour]);

  async function generate() {
    setRouteLine(null);
    setRouteInfo(null);
    setError("");
    setLoading(true);

    try {
      const s = await api.routeStats(originId, destId);
      setStats(s);

      const info = await api.routeInfo(originId, destId);
      setRouteInfo(info);

      const points = polyline.decode(info.encoded_polyline);
      setRouteLine(points);
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setLoading(false);
    }

    const hours = await api.recommendationsByRouteHour(originId, destId, 1, 24); 
    setByHour(hours);
  }

  return (
    <div className="page">
    
    <div style={{ height: 600 }} />

    <PageHeader
      title="Commute Analysis"
      subtitle="Compare historical data for a specific route to find the best travel window."
    />

      {error && <Alert>{error}</Alert>}

      <div className="split">
        {/* Left */}
        <div className="panel panelPad">
          <div className="sectionTitle">Route</div>

          <div className="formRow">
            <Field label="Origin">
              <select className="select" value={originId} onChange={(e) => setOriginId(e.target.value)}>
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>{l.name}</option>
                ))}
              </select>
            </Field>

            <Field label="Destination">
              <select className="select" value={destId} onChange={(e) => setDestId(e.target.value)}>
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>{l.name}</option>
                ))}
              </select>
            </Field>
          </div>

          <button
            className="btn btnPrimary btnWide"
            onClick={generate}
            disabled={!originId || !destId || originId === destId || loading}
            style={{ marginTop: 10 }}
          >
            {loading ? "Generating…" : "Generate Trend Insights"}
          </button>

          <div style={{ marginTop: 12 }}>
            <div className="sectionTitle">Log Commute</div>

            <Field label="Actual minutes (what it took)">
              <input
                className="input"
                type="number"
                min="1"
                value={actualMinutes}
                onChange={(e) => setActualMinutes(e.target.value)}
                placeholder="e.g., 42"
              />
            </Field>

            <button
              className="btn btnWide"
              style={{ marginTop: 10 }}
              disabled={!originId || !destId || originId === destId || !actualMinutes || loading}
              onClick={async () => {
                setError("");
                setLogStatus("");
                try {
                  await api.createCommute({
                    origin_location_id: Number(originId),
                    destination_location_id: Number(destId),
                    actual_minutes: Number(actualMinutes),
                    use_api_estimate: true,
                  });
                  setLogStatus("Commute logged ✅ (estimate pulled from Google)");
                  setActualMinutes("");
                } catch (e) {
                  setError(String(e?.message || e));
                }
              }}
            >
              Log Commute (Auto-estimate)
            </button>

            {logStatus && <div className="note" style={{ marginTop: 8 }}>{logStatus}</div>}
          </div>

          <div className="note">
            Tip: CommuteWise uses aggregated historical data to build these trends. This view does not account for real-time incidents or weather.
          </div>

          <hr className="hr" />

          <div className="sectionTitle">Insights</div>

            {routeInfo && (
            <div className="panel" style={{ padding: 12, marginBottom: 12 }}>
              <div style={{ display: "grid", gap: 8 }}>
                <Row label="Live ETA" value={`${Math.round(routeInfo.duration_seconds / 60)} min`} />
                <Row
                  label="Distance"
                  value={`${(routeInfo.distance_meters / 1609.34).toFixed(1)} mi`}
                />
              </div>
            </div>
          )}

            {routeInfo && historicalNow && (
              <div className="panel" style={{ padding: 12, marginBottom: 12 }}>
              <div className="muted" style={{ fontWeight: 900, marginBottom: 8 }}>
                Live vs Historical
              </div>

              <div style={{ display: "grid", gap: 8 }}>
                <Row label="Live ETA" value={`${Math.round(routeInfo.duration_seconds / 60)} min`} />

                {historicalNow.match ? (
                  <>
                    <Row
                      label={`Historical @ ${String(historicalNow.currentHour).padStart(2, "0")}:00`}
                      value={`${historicalNow.match.avg_actual_minutes} min`}
                    />
                    <Row
                      label="Typical slowdown"
                      value={`${historicalNow.match.percent_worse_than_estimated}% worse`}
                    />
                  </>
                ) : (
                  <div className="muted">
                    Not enough historical samples for {String(historicalNow.currentHour).padStart(2, "0")}:00.
                  </div>
                )}
              </div>
            </div>
          )}

            {bestWorst && (
            <div className="panel" style={{ padding: 12, marginBottom: 12 }}>
              <div className="muted" style={{ fontWeight: 900, marginBottom: 8 }}>
                Best travel windows (historical)
              </div>

              <div style={{ display: "grid", gap: 8, marginBottom: 10 }}>
                {bestWorst.best.map((h) => (
                  <div key={`best-${h.hour}`} style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                    <div style={{ fontWeight: 900 }}>{String(h.hour).padStart(2, "0")}:00</div>
                    <div className="muted">
                      {h.percent_worse_than_estimated}% worse • n={h.count}
                    </div>
                  </div>
                ))}
              </div>

              <div className="muted" style={{ fontWeight: 900, marginBottom: 8 }}>
                Worst travel windows (historical)
              </div>

              <div style={{ display: "grid", gap: 8 }}>
                {bestWorst.worst.map((h) => (
                  <div key={`worst-${h.hour}`} style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                    <div style={{ fontWeight: 900 }}>{String(h.hour).padStart(2, "0")}:00</div>
                    <div className="muted">
                      {h.percent_worse_than_estimated}% worse • n={h.count}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

            {byHour && byHour.length > 0 && (
            <div className="panel" style={{ padding: 12 }}>
              <div className="muted" style={{ fontWeight: 900, marginBottom: 8 }}>
                Hourly trend (historical)
              </div>
              <div style={{ display: "grid", gap: 6 }}>
                {[...byHour]
                  .sort((a, b) => a.hour - b.hour)
                  .map((h) => (
                    <div key={h.hour} style={{ display: "flex", justifyContent: "space-between" }}>
                      <div style={{ fontWeight: 900 }}>{String(h.hour).padStart(2, "0")}:00</div>
                      <div className="muted">{h.percent_worse_than_estimated}% • n={h.count}</div>
                    </div>
                  ))}
              </div>
            </div>
          )}

            {bestWorst?.best?.[0] && (
              <div className="note" style={{ marginTop: 8 }}>
                Recommendation: If you can, try leaving around{" "}
                <b>{String(bestWorst.best[0].hour).padStart(2, "0")}:00</b> — historically it has the lowest delay for this route.
              </div>
          )}

          {!stats ? (
            <p className="muted">Select a route and click “Generate Trend Insights”.</p>
          ) : stats.count === 0 ? (
            <p className="muted">No commutes found for this route yet.</p>
          ) : (
            <div className="panel" style={{ padding: 12 }}>
              <div style={{ display: "grid", gap: 8 }}>
                <Row label="Samples" value={stats.count} />
                <Row label="Avg Estimated" value={`${stats.avg_estimated_minutes} min`} />
                <Row label="Avg Actual" value={`${stats.avg_actual_minutes} min`} />
                <Row label="% Worse" value={`${stats.percent_worse_than_estimated}%`} />
              </div>
            </div>
          )}
        </div>

        {/* Right */}
        <div className="panel panelPad">
          <div className="sectionTitle">Map</div>

          <MapContainer
            center={[47.6062, -122.3321]}
            zoom={10}
            style={{ height: 520, width: "100%", borderRadius: 12 }}
          >
            <TileLayer
              attribution='&copy; OpenStreetMap contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {routeLine && <Polyline positions={routeLine} weight={4} />}

            {/* Markers from saved locations (if lat/lng exist) */}
              {origin?.lat != null && origin?.lng != null && (
                <Marker position={[origin.lat, origin.lng]}>
                  <Popup>Origin: {origin.name}</Popup>
                </Marker>
              )}

              {dest?.lat != null && dest?.lng != null && (
                <Marker position={[dest.lat, dest.lng]}>
                  <Popup>Destination: {dest.name}</Popup>
                </Marker>
              )}
          </MapContainer>

          <p className="muted" style={{ marginTop: 10 }}>
            * Route visuals and stats are based on sample commute data and are for demonstration only.
          </p>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
      <div className="muted" style={{ fontWeight: 800 }}>{label}</div>
      <div style={{ fontWeight: 900 }}>{value}</div>
    </div>
  );
}