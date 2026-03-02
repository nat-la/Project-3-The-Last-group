import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Alert, KPI, PageHeader } from "../components/ui";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [byHour, setByHour] = useState(null);
  const [routeRecs, setRouteRecs] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

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
        setError(String(e?.message || e));
      }
    })();
  }, []);

  const { best, worst } = useMemo(() => {
    if (!byHour?.length) return { best: null, worst: null };
    const sortedAsc = [...byHour].sort((a, b) => a.avg_delay_minutes - b.avg_delay_minutes);
    const sortedDesc = [...byHour].sort((a, b) => b.avg_delay_minutes - a.avg_delay_minutes);
    return { best: sortedAsc[0], worst: sortedDesc[0] };
  }, [byHour]);

  const padHour = (h) => `${String(h).padStart(2, "0")}:00`;

  return (
    <div className="page">

      <div style={{ height: 340 }} />

      <PageHeader
        title="Master Your Daily Commute"
        subtitle="Analyze historical traffic trends to reclaim your time. CommuteWise helps you find the best departure window based on long-term data."
        right={
          <>
            <button className="btn btnPrimary" onClick={() => navigate("/analyze")}>
              Analyze commute
            </button>

            <button className="btn" onClick={() => navigate("/locations")}>
              Add location
            </button>
          </>
        }
      />

      {error && <Alert>{error}</Alert>}

      <div className="grid3">
        <KPI
          label="Avg. Commute Time"
          value={summary ? `${summary.avg_actual_minutes} min` : "…"}
          sub="Based on all commutes"
        />
        <KPI
          label="Worst Congestion"
          value={worst ? padHour(worst.hour) : "…"}
          sub={worst ? `Avg delay ${worst.avg_delay_minutes} min` : " "}
        />
        <KPI
          label="Best Window"
          value={best ? padHour(best.hour) : "…"}
          sub={best ? `Save ~${Math.max(0, worst?.avg_delay_minutes - best.avg_delay_minutes)} min vs worst` : " "}
        />
      </div>

      <div className="panel panelPad" style={{ marginTop: 14 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
          <div>
            <div className="sectionTitle" style={{ marginBottom: 4 }}>Top Route Issues</div>
            <div className="muted">Routes with consistently higher actual time vs estimate.</div>
          </div>
          <button className="btn" onClick={() => navigate("/locations")}>
              Manage locations
            </button>
        </div>

        <hr className="hr" />

        {!routeRecs ? (
          <p className="muted">Loading…</p>
        ) : routeRecs.length === 0 ? (
          <p className="muted">No flagged routes yet.</p>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {routeRecs.slice(0, 5).map((r, i) => (
              <div key={i} className="panel" style={{ padding: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
                  <div style={{ fontWeight: 900 }}>
                    Route {r.origin_location_id} → {r.destination_location_id}
                  </div>
                  <span className="badge">{r.percent_worse_than_estimated}% worse</span>
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  Higher-than-expected travel time detected from historical samples.
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}