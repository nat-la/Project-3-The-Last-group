import { useEffect, useState } from "react";
import { api } from "../api";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [byHour, setByHour] = useState(null);
  const [routeRecs, setRouteRecs] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [sum, hour, recs] = await Promise.all([
          api.summary(),
          api.byHour(),
          api.recommendationsByRoute(0.15, 5, 10),
        ]);
        setSummary(sum);
        setByHour(hour);
        setRouteRecs(recs);
      } catch (e) {
        setError(String(e.message || e));
      }
    })();
  }, []);

  // simple “best hour” + “worst hour” from byHour
  let best = null, worst = null;
  if (byHour && byHour.length) {
    best = [...byHour].sort((a, b) => a.avg_delay_minutes - b.avg_delay_minutes)[0];
    worst = [...byHour].sort((a, b) => b.avg_delay_minutes - a.avg_delay_minutes)[0];
  }

  return (
    <div style={{ padding: 20 }}>
      <h1>Dashboard</h1>
      {error && <div style={{ background: "#fee", padding: 10 }}>{error}</div>}

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Card title="Avg Commute Time" value={summary ? `${summary.avg_actual_minutes} min` : "…"} subtitle="Based on all commutes" />
        <Card title="Worst Hour" value={worst ? `${String(worst.hour).padStart(2,"0")}:00` : "…"} subtitle={worst ? `Avg delay ${worst.avg_delay_minutes} min` : ""} />
        <Card title="Best Hour" value={best ? `${String(best.hour).padStart(2,"0")}:00` : "…"} subtitle={best ? `Avg delay ${best.avg_delay_minutes} min` : ""} />
      </div>

      <h2 style={{ marginTop: 24 }}>Top Route Issues</h2>
      {!routeRecs ? (
        <p>Loading…</p>
      ) : routeRecs.length === 0 ? (
        <p>No flagged routes yet.</p>
      ) : (
        <ul>
          {routeRecs.slice(0, 5).map((r, i) => (
            <li key={i}>
              Route {r.origin_location_id} → {r.destination_location_id}: {r.percent_worse_than_estimated}% worse
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Card({ title, value, subtitle }) {
  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 10, padding: 14, width: 260 }}>
      <div style={{ fontSize: 12, opacity: 0.7 }}>{title}</div>
      <div style={{ fontSize: 26, fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: 12, opacity: 0.7 }}>{subtitle}</div>
    </div>
  );
}
