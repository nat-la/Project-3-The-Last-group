/**
 * App entry point (Vite + React 18)
 *
 * Responsibilities:
 * - Import global styles and side-effect modules
 * - Initialize React root using createRoot (concurrent mode)
 * - Render <App /> inside StrictMode
 */

import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App.jsx";

/**
 * Global styles
 *
 * NOTE:
 * - index.css = Vite template defaults (may conflict with your custom layout system)
 * - ui.css = your actual design system (panels, layout, navbar, etc.)
 *
 * Order matters: later imports override earlier ones.
 */
import "./index.css";
import "leaflet/dist/leaflet.css"; // Required for proper Leaflet map rendering
import "./leafletFix";             // Side-effect import to patch Leaflet marker icons
import "./styles/ui.css";

/**
 * Bootstrap React app
 *
 * createRoot enables React 18 concurrent features.
 * StrictMode intentionally double-invokes some lifecycle logic in dev
 * to surface unsafe side effects (no impact in production build).
 */
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);