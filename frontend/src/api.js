const API = import.meta.env.VITE_API;

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${txt}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return null;
}

export const api = {
  root: () => request("/"),

  listLocations: () => request("/locations"),

  createLocation: (data) => request("/locations", { method: "POST", body: JSON.stringify(data) }),

  listCommutes: () => request("/commutes"),

  createCommute: (data) => request("/commutes", { method: "POST", body: JSON.stringify(data) }),

  summary: () => request("/analytics/summary"),

  byHour: () => request("/analytics/by-hour"),

  recommendations: () => request("/analytics/recommendations"),

  seedCommutes: (n = 60) => request(`/debug/seed-commutes?n=${n}`, { method: "POST" }),

  recommendationsByRoute: (pct_threshold = 0.15, min_samples = 5, top = 10) => request(
    `/analytics/recommendations-by-route?pct_threshold=${pct_threshold}&min_samples=${min_samples}&top=${top}`),

  recommendationsByRouteHour: (originId, destId, minSamples = 1, top = 24, pctThreshold = 0.15) =>
  request(
    `/analytics/recommendations-by-route-hour?origin_id=${originId}&destination_id=${destId}` +
    `&min_samples=${minSamples}&top=${top}&pct_threshold=${pctThreshold}`
  ),

  routeStats: (originId, destinationId) =>
    request(`/analytics/route-stats?origin_id=${originId}&destination_id=${destinationId}`),

  routeInfo: (originId, destinationId) =>
    request(`/routes/info?origin_id=${originId}&destination_id=${destinationId}`),

  deleteLocation: (id) => request(`/locations/${id}`, {method: "DELETE"}),
};

const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
document.documentElement.style.setProperty('--scrollbar-width', `${scrollbarWidth}px`);
