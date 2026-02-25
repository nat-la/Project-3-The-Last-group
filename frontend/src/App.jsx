import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Locations from "./pages/Locations";
import Analyze from "./pages/Analyze";

export default function App() {
  return (
    <BrowserRouter>
      <TopNav />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/locations" element={<Locations />} />
        <Route path="/analyze" element={<Analyze />} />
      </Routes>
    </BrowserRouter>
  );
}

function TopNav() {
  const linkStyle = ({ isActive }) => ({
    padding: "8px 12px",
    borderRadius: 8,
    textDecoration: "none",
    color: "black",
    background: isActive ? "#eef" : "transparent",
  });

  return (
    <div style={{ display: "flex", gap: 10, padding: 12, borderBottom: "1px solid #ddd" }}>
      <div style={{ fontWeight: 800 }}>CommuteWise</div>
      <NavLink to="/" style={linkStyle}>Dashboard</NavLink>
      <NavLink to="/locations" style={linkStyle}>Locations</NavLink>
      <NavLink to="/analyze" style={linkStyle}>Analyze</NavLink>
    </div>
  );
}
