/**
 * App (routing + global shell)
 *
 * Responsibilities:
 * - Configure client-side routes (Dashboard / Locations / Analyze)
 * - Render a fixed top navbar
 * - Compute navbar height at runtime and store it in CSS variable --navH
 *   so main content can be padded down (avoids being hidden under fixed navbar).
 */

import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { useEffect, useRef } from "react";
import Dashboard from "./pages/Dashboard";
import Locations from "./pages/Locations";
import Analyze from "./pages/Analyze";

export default function App() {
  // Ref to the navbar DOM node so we can measure its rendered height.
  const navRef = useRef(null);

  useEffect(() => {
    /**
     * setNavHeight()
     * Measures the current navbar height and writes it into a CSS variable:
     *   --navH: <px>
     *
     * .appMain uses this var for padding-top to offset fixed navbar.
     */
    const setNavHeight = () => {
      const h = navRef.current?.offsetHeight ?? 0;
      document.documentElement.style.setProperty("--navH", `${h}px`);
    };

    // Run immediately on mount (initial layout)
    setNavHeight();

    // Keep it correct on window resize (responsive layout / wrapping)
    window.addEventListener("resize", setNavHeight);

    // Extra pass after first paint to catch late layout changes (font loading, etc.)
    requestAnimationFrame(setNavHeight);

    // Cleanup listener on unmount
    return () => window.removeEventListener("resize", setNavHeight);
  }, []);

  return (
    <BrowserRouter>
      <div className="appShell">
        {/* Fixed navbar at top; measured via navRef */}
        <TopNav navRef={navRef} />

        {/* Main content area is padded by --navH to avoid overlap with fixed navbar */}
        <main className="appMain">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/locations" element={<Locations />} />
            <Route path="/analyze" element={<Analyze />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

/**
 * TopNav
 * Pure presentational navbar with:
 * - Left: simple "C" badge + product name/version
 * - Right: NavLinks that add an "active" class for styling
 *
 * Note:
 * - The root node has className "navbar" which is position:fixed in CSS.
 * - navRef is attached so App can measure the height for content offset.
 */
function TopNav({ navRef }) {
  return (
    <div className="navbar" ref={navRef}>
      {/* Left: brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* App mark */}
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: "var(--blue)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            fontWeight: 900,
            fontSize: 14,
          }}
        >
          C
        </div>

        {/* App name + version */}
        <div style={{ fontWeight: 900, fontSize: 14 }}>
          CommuteWise{" "}
          <span style={{ color: "var(--muted)", fontWeight: 600 }}>v0.1 MVP</span>
        </div>
      </div>

      {/* Right: route navigation */}
      <div style={{ display: "flex", gap: 6 }}>
        {/* NavLink provides isActive so we can toggle active styling */}
        <NavLink
          to="/"
          className={({ isActive }) => (isActive ? "navlink active" : "navlink")}
        >
          Dashboard
        </NavLink>

        <NavLink
          to="/locations"
          className={({ isActive }) => (isActive ? "navlink active" : "navlink")}
        >
          Locations
        </NavLink>

        <NavLink
          to="/analyze"
          className={({ isActive }) => (isActive ? "navlink active" : "navlink")}
        >
          Analyze
        </NavLink>
      </div>
    </div>
  );
}