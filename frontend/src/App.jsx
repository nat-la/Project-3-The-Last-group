import { useEffect, useState } from "react";
import { api } from "./api";

const API = import.meta.env.VITE_API;

export default function App() {
  const [msg, setMsg] = useState("loading...");
  const [error, setError] = useState("");

  // Locations
  const [locations, setLocations] = useState([]);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [savingLocation, setSavingLocation] = useState(false);

  // Commutes
  const [commutes, setCommutes] = useState([]);
  const [originId, setOriginId] = useState("");
  const [destId, setDestId] = useState("");
  const [estimated, setEstimated] = useState("");
  const [actual, setActual] = useState("");
  const [savingCommute, setSavingCommute] = useState(false);

  // Analytics
  const [summary, setSummary] = useState(null);
  const [recs, setRecs] = useState(null);
  const [routeRecs, setRouteRecs] = useState(null);
  const [byHour, setByHour] = useState(null);
  const [routeHourRecs, setRouteHourRecs] = useState(null);


  async function refreshAll() {
    setError("");
    try {
      const [root, locs, comms, sum, rec, routeRecsData, byHourData, routeHourRecsData] = await Promise.all([
        api.root(),
        api.listLocations(),
        api.listCommutes(),
        api.summary(),
        api.recommendations(),
        api.recommendationsByRoute(0.15,5,10), // should be 0.15, 5, 10 but 0.1, 3, 10 for testing
        api.byHour(),
        api.recommendationsByRouteHour(0.10,3,20)
      ]);

      setMsg(root.message);
      setLocations(locs);
      setCommutes(comms);
      setSummary(sum);
      setRecs(rec);
      setRouteRecs(routeRecsData);
      setByHour(byHourData);
      setRouteHourRecs(routeHourRecsData);

      // Set default dropdown values if empty
      if (locs.length >= 2) {
        if (!originId) setOriginId(String(locs[0].id));
        if (!destId) setDestId(String(locs[1].id));
      }
    } catch (e) {
      setError(String(e.message || e));
    }
  }

  useEffect(() => {
    refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function addLocation(e) {
    e.preventDefault();
    setError("");
    setSavingLocation(true);

    try {
      await api.createLocation({ name, address });
      setName("");
      setAddress("");
      await refreshAll();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSavingLocation(false);
    }
  }

  async function addCommute(e) {
    e.preventDefault();
    setError("");
    setSavingCommute(true);

    try {
      if (!originId || !destId) throw new Error("Pick an origin and destination");
      if (originId === destId) throw new Error("Origin and destination must be different");

      const payload = {
        origin_location_id: Number(originId),
        destination_location_id: Number(destId),
        mode: "driving",
        estimated_minutes: Number(estimated),
        actual_minutes: Number(actual),
      };

      await api.createCommute(payload);

      setEstimated("");
      setActual("");
      await refreshAll();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSavingCommute(false);
    }
  }

  async function seedCommutes() {
    setError("");
    try {
      await api.seedCommutes(60);
      await refreshAll();
    } catch (e) {
      setError(String(e.message || e));
    }
  }

  const idToName = new Map(locations.map((l) => [l.id, l.name]));

  return (
    <div style={{ fontFamily: "system-ui", padding: 20, maxWidth: 1000, margin: "0 auto" }}>
      <h1>Mapping Project (Dev UI)</h1>

      {error && (
        <div style={{ background: "#fee", padding: 12, borderRadius: 8, marginBottom: 12 }}>
          <b>Error:</b> {error}
        </div>
      )}

      <p>
        <b>Backend says:</b> {msg}
      </p>

      {/* LOCATIONS */}
      <section style={{ marginTop: 20, padding: 12, border: "1px solid #ddd", borderRadius: 10 }}>
        <h2>Saved Locations</h2>

        <form onSubmit={addLocation} style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <input
            placeholder="Name (Home, Work)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            placeholder="Address"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            required
            style={{ flex: 1 }}
          />
          <button type="submit" disabled={savingLocation}>
            {savingLocation ? "Saving..." : "Add"}
          </button>
        </form>

        {locations.length === 0 ? (
          <p>No locations yet.</p>
        ) : (
          <ul>
            {locations.map((l) => (
              <li key={l.id}>
                <b>{l.name}</b> — {l.address} (id: {l.id})
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* COMMUTES */}
      <section style={{ marginTop: 20, padding: 12, border: "1px solid #ddd", borderRadius: 10 }}>
        <h2>Log Commute</h2>

        {locations.length < 2 ? (
          <p>Add at least 2 locations first (origin + destination).</p>
        ) : (
          <form onSubmit={addCommute} style={{ display: "grid", gap: 10, maxWidth: 700 }}>
            <div style={{ display: "flex", gap: 10 }}>
              <label style={{ flex: 1 }}>
                Origin<br />
                <select value={originId} onChange={(e) => setOriginId(e.target.value)} required>
                  {locations.map((l) => (
                    <option key={l.id} value={String(l.id)}>
                      {l.name} (id {l.id})
                    </option>
                  ))}
                </select>
              </label>

              <label style={{ flex: 1 }}>
                Destination<br />
                <select value={destId} onChange={(e) => setDestId(e.target.value)} required>
                  {locations.map((l) => (
                    <option key={l.id} value={String(l.id)}>
                      {l.name} (id {l.id})
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <label style={{ flex: 1 }}>
                Estimated minutes<br />
                <input
                  type="number"
                  min="1"
                  value={estimated}
                  onChange={(e) => setEstimated(e.target.value)}
                  required
                />
              </label>

              <label style={{ flex: 1 }}>
                Actual minutes<br />
                <input
                  type="number"
                  min="1"
                  value={actual}
                  onChange={(e) => setActual(e.target.value)}
                  required
                />
              </label>

              <div style={{ alignSelf: "end" }}>
                <button type="submit" disabled={savingCommute}>
                  {savingCommute ? "Logging..." : "Log commute"}
                </button>
              </div>
            </div>
          </form>
        )}

        <div style={{ marginTop: 12 }}>
          <button onClick={seedCommutes}>Seed 60 Commutes (Dev)</button>
        </div>

        <h3 style={{ marginTop: 16 }}>Recent Commutes</h3>
        {commutes.length === 0 ? (
          <p>No commutes yet.</p>
        ) : (
          <ul>
            {commutes.slice(0, 10).map((c) => (
              <li key={c.id}>
                #{c.id} —{" "}
                <b>{idToName.get(c.origin_location_id) || c.origin_location_id}</b> →{" "}
                <b>{idToName.get(c.destination_location_id) || c.destination_location_id}</b>{" "}
                | est {c.estimated_minutes} / actual {c.actual_minutes} | {String(c.started_at)}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ANALYTICS */}
      <section style={{ marginTop: 20, padding: 12, border: "1px solid #ddd", borderRadius: 10 }}>
        <h2>Analytics</h2>

        <h3>Summary</h3>
        <pre>{JSON.stringify(summary, null, 2)}</pre>

        <h3>Route Recommendations</h3>

        {routeRecs === null ? (
          <p>Loading...</p>
        ) : routeRecs.length === 0 ? (
          <p>No route recommendations yet (try seeding more commutes or lowering the threshold).</p>
        ) : (
          <table border="1" cellPadding="6" style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th>Route</th>
                <th>Samples</th>
                <th>Avg Est</th>
                <th>Avg Actual</th>
                <th>% Worse</th>
                <th>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {routeRecs.map((r, idx) => (
                <tr
                  key={idx}
                  style={{
                    backgroundColor: r.is_flagged ? "#fff3cd" : "transparent"
                  }}
                >
                  <td>
                    {(idToName.get(r.origin_location_id) || r.origin_location_id) +
                      " → " +
                      (idToName.get(r.destination_location_id) || r.destination_location_id)}
                  </td>
                  <td>{r.count}</td>
                  <td>{r.avg_estimated_minutes}</td>
                  <td>{r.avg_actual_minutes}</td>
                  <td>{r.percent_worse_than_estimated}%</td>
                  <td>{r.recommendation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <h3>By Hour</h3>
      {byHour === null ? (
        <p>Loading...</p>
      ) : (
        <table border="1" cellPadding="6" style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th>Hour</th>
              <th>Count</th>
              <th>Avg Est</th>
              <th>Avg Actual</th>
              <th>Avg Delay</th>
            </tr>
          </thead>
          <tbody>
            {byHour.map((r) => (
              <tr key={r.hour}>
                <td>{String(r.hour).padStart(2, "0")}:00</td>
                <td>{r.count}</td>
                <td>{r.avg_estimated_minutes}</td>
                <td>{r.avg_actual_minutes}</td>
                <td>{r.avg_delay_minutes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3 style={{ marginTop: 16 }}>Route + Hour Recommendations</h3>
      {routeHourRecs === null ? (
        <p>Loading...</p>
      ) : routeHourRecs.length === 0 ? (
        <p>No route+hour recommendations yet (try seeding more or lowering threshold).</p>
      ) : (
        <table border="1" cellPadding="6" style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th>Route</th>
              <th>Hour</th>
              <th>Samples</th>
              <th>Avg Est</th>
              <th>Avg Actual</th>
              <th>% Worse</th>
            </tr>
          </thead>
          <tbody>
            {routeHourRecs.map((r, idx) => (
              <tr key={idx}>
                <td>
                  {(idToName.get(r.origin_location_id) || r.origin_location_id) +
                    " → " +
                    (idToName.get(r.destination_location_id) || r.destination_location_id)}
                </td>
                <td>{String(r.hour).padStart(2, "0")}:00</td>
                <td>{r.count}</td>
                <td>{r.avg_estimated_minutes}</td>
                <td>{r.avg_actual_minutes}</td>
                <td>{r.percent_worse_than_estimated}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
