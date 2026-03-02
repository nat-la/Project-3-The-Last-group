/**
 * Dashboard page
 *
 * Purpose:
 * - Landing view with high-level KPIs (avg commute time, best/worst congestion hour)
 * - Shows a "Top Route Issues" list based on historical underperformance vs estimates
 * - Provides navigation CTAs into Analyze + Locations flows
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Alert, KPI, PageHeader } from "../components/ui";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  // Summary aggregates for all commutes
  const [summary, setSummary] = useState(null);

  // Hourly aggregates (e.g. avg delay minutes per hour bucket)
  const [byHour, setByHour] = useState(null);

  // Route-level recommendations / flags (routes consistently worse than estimated)
  const [routeRecs, setRouteRecs] = useState(null);

  // Global error banner message
  const [error, setError] = useState("");

  // Router navigation helper
  const navigate = useNavigate();

  /**
   * Initial data load:
   * - summary(): global aggregates (avg actual, etc.)
   * - byHour(): hourly bucket aggregates for “best/worst hour”
   * - recommendationsByRoute(): worst routes by % worse than estimated
   *
   * Promise.all runs these concurrently to keep first paint snappy.
   */
  useEffect(() => {
    (async () => {
      try {
        const [sum, hour, recs] = await Promise.all([
          api.summary(),
          api.byHour(),
          // params likely represent: min_worse_ratio, min_samples, limit
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

  /**
   * Compute the “best” and “worst” hours from the byHour data.
   * Uses avg_delay_minutes as the optimization metric.
   */
  const { best, worst } = useMemo(() => {
    if (!byHour?.length) return { best: null, worst: null };

    // Best = smallest avg delay; Worst = largest avg delay
    const sortedAsc = [...byHour].sort((a, b) => a.avg_delay_minutes - b.avg_delay_minutes);
    const sortedDesc = [...byHour].sort((a, b) => b.avg_delay_minutes - a.avg_delay_minutes);

    return { best: sortedAsc[0], worst: sortedDesc[0] };
  }, [byHour]);

  // Display helper: render hours as "HH:00"
  const padHour = (h) => `${String(h).padStart(2, "0")}:00`;

  return (
    <div className="page">
      {/* Spacer: likely used to offset fixed header/nav.
          If the layout feels “pushed down”, this is a prime suspect. */}
      <div style={{ height: 340 }} />

      <PageHeader
        title="Master Your Daily Commute"
        subtitle="Analyze historical traffic trends to reclaim your time. CommuteWise helps you find the best departure window based on long-term data."
        right={
          <>
            {/* Primary CTA: go to route analysis */}
            <button className="btn btnPrimary" onClick={() => navigate("/analyze")}>
              Analyze commute
            </button>

            {/* Secondary CTA: add/manage locations */}
            <button className="btn" onClick={() => navigate("/locations")}>
              Add location
            </button>
          </>
        }
      />

      {/* Global error banner */}
      {error && <Alert>{error}</Alert>}

      {/* KPI row: summary, worst hour, best hour */}
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
          // Estimates potential savings relative to the worst hour
          sub={
            best
              ? `Save ~${Math.max(0, worst?.avg_delay_minutes - best.avg_delay_minutes)} min vs worst`
              : " "
          }
        />
      </div>

      {/* Route-level issues list */}
      <div className="panel panelPad" style={{ marginTop: 14 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 10,
          }}
        >
          <div>
            <div className="sectionTitle" style={{ marginBottom: 4 }}>
              Top Route Issues
            </div>
            <div className="muted">Routes with consistently higher actual time vs estimate.</div>
          </div>

          {/* Jump to locations management (likely where routes are defined) */}
          <button className="btn" onClick={() => navigate("/locations")}>
            Manage locations
          </button>
        </div>

        <hr className="hr" />

        {/* Loading / empty / populated states */}
        {!routeRecs ? (
          <p className="muted">Loading…</p>
        ) : routeRecs.length === 0 ? (
          <p className="muted">No flagged routes yet.</p>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {/* Limit display to top 5 (even if API returned more) */}
            {routeRecs.slice(0, 5).map((r, i) => (
              <div key={i} className="panel" style={{ padding: 12 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 10,
                    alignItems: "center",
                  }}
                >
                  {/* NOTE: This currently displays raw location IDs.
                      If you want names, you'd need a join/lookup against locations. */}
                  <div style={{ fontWeight: 900 }}>
                    Route {r.origin_location_id} → {r.destination_location_id}
                  </div>

                  {/* Primary metric for "flagged" status */}
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