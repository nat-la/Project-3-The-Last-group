import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { useEffect, useRef } from "react";
import Dashboard from "./pages/Dashboard";
import Locations from "./pages/Locations";
import Analyze from "./pages/Analyze";

export default function App() {
  const navRef = useRef(null);

  useEffect(() => {
    const setNavHeight = () => {
      const h = navRef.current?.offsetHeight ?? 0;
      document.documentElement.style.setProperty("--navH", `${h}px`);
    };

    setNavHeight();

    // keep it correct if fonts load / window resizes
    window.addEventListener("resize", setNavHeight);

    // extra: recalc after first paint
    requestAnimationFrame(setNavHeight);

    return () => window.removeEventListener("resize", setNavHeight);
  }, []);

  return (
    <BrowserRouter>
      <div className="appShell">
        <TopNav navRef={navRef} />
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

function TopNav({ navRef }) {
  return (
    <div className="navbar" ref={navRef}>
      {/* Left */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
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
        <div style={{ fontWeight: 900, fontSize: 14 }}>
          CommuteWise <span style={{ color: "var(--muted)", fontWeight: 600 }}>v0.1 MVP</span>
        </div>
      </div>

      {/* Right */}
      <div style={{ display: "flex", gap: 6 }}>
        <NavLink to="/" className={({ isActive }) => (isActive ? "navlink active" : "navlink")}>
          Dashboard
        </NavLink>
        <NavLink to="/locations" className={({ isActive }) => (isActive ? "navlink active" : "navlink")}>
          Locations
        </NavLink>
        <NavLink to="/analyze" className={({ isActive }) => (isActive ? "navlink active" : "navlink")}>
          Analyze
        </NavLink>
      </div>
    </div>
  );
}