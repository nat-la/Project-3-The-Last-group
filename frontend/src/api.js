/**
 * api client wrapper
 *
 * Purpose:
 * - Centralize fetch() calls to the backend using a Vite-provided base URL
 * - Normalize JSON headers + response parsing
 * - Throw useful errors (status + body text) for non-2xx responses
 *
 * Assumptions:
 * - VITE_API is set (e.g., "http://127.0.0.1:8000") and does NOT end with a trailing slash
 *   unless your paths account for it.
 */

const API = import.meta.env.VITE_API;

/**
 * request()
 * Low-level fetch helper:
 * - Prepends API base URL
 * - Defaults Content-Type to JSON
 * - Throws on non-OK responses with body text for debugging
 * - Returns parsed JSON if response is JSON, else returns null
 */
async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  // Convert backend errors into exceptions with maximum debug context.
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${txt}`);
  }

  // Only attempt JSON parsing when server says it returned JSON.
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();

  // For endpoints that return no body (e.g., DELETE), treat as null/void.
  return null;
}

/**
 * High-level API surface used by the React pages.
 * Keeps the pages clean and makes it easy to change endpoint paths in one place.
 */
export const api = {
  // Health/root endpoint
  root: () => request("/"),

  // Locations CRUD
  listLocations: () => request("/locations"),
  createLocation: (data) =>
    request("/locations", { method: "POST", body: JSON.stringify(data) }),
  deleteLocation: (id) =>
    request(`/locations/${id}`, { method: "DELETE" }),

  // Commutes CRUD
  listCommutes: () => request("/commutes"),
  createCommute: (data) =>
    request("/commutes", { method: "POST", body: JSON.stringify(data) }),

  // Analytics endpoints
  summary: () => request("/analytics/summary"),
  byHour: () => request("/analytics/by-hour"),
  recommendations: () => request("/analytics/recommendations"),

  // Debug helper to seed sample data on the backend
  seedCommutes: (n = 60) =>
    request(`/debug/seed-commutes?n=${n}`, { method: "POST" }),

  /**
   * Route-level recommendations:
   * Flags routes whose avg actual time is >= (1 + pct_threshold) * estimated
   * min_samples filters noisy/insufficient data.
   * top limits returned routes.
   */
  recommendationsByRoute: (pct_threshold = 0.15, min_samples = 5, top = 10) =>
    request(
      `/analytics/recommendations-by-route?pct_threshold=${pct_threshold}&min_samples=${min_samples}&top=${top}`
    ),

  /**
   * Hour-by-hour breakdown for a specific origin/destination pair.
   * Used on Analyze page to show best/worst travel windows by hour.
   */
  recommendationsByRouteHour: (
    originId,
    destId,
    minSamples = 1,
    top = 24,
    pctThreshold = 0.15
  ) =>
    request(
      `/analytics/recommendations-by-route-hour?origin_id=${originId}&destination_id=${destId}` +
        `&min_samples=${minSamples}&top=${top}&pct_threshold=${pctThreshold}`
    ),

  // Aggregated stats for a specific route (samples, averages, % worse)
  routeStats: (originId, destinationId) =>
    request(`/analytics/route-stats?origin_id=${originId}&destination_id=${destinationId}`),

  // Live route details (ETA, distance, encoded polyline) for map rendering
  routeInfo: (originId, destinationId) =>
    request(`/routes/info?origin_id=${originId}&destination_id=${destinationId}`),
};

/**
 * UI layout helper:
 * Computes the width of the vertical scrollbar and stores it in a CSS variable.
 * Used by the navbar width calculation:
 *   width: calc(100vw - var(--scrollbar-width));
 *
 * NOTE: This runs once at module load time. If the viewport resizes (or scrollbar
 * presence changes), the value can become stale unless you also update on resize.
 */
const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
document.documentElement.style.setProperty("--scrollbar-width", `${scrollbarWidth}px`);