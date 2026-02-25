import { useEffect, useState } from "react";
import { api } from "../api";

export default function Locations() {
  const [locations, setLocations] = useState([]);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    setError("");
    try {
      setLocations(await api.listLocations());
    } catch (e) {
      setError(String(e.message || e));
    }
  }

  useEffect(() => { refresh(); }, []);

  async function add(e) {
    e.preventDefault();
    setError("");
    try {
      await api.createLocation({ name, address });
      setName(""); setAddress("");
      await refresh();
    } catch (e) {
      setError(String(e.message || e));
    }
  }

  return (
    <div style={{ padding: 20 }}>
      <h1>Locations</h1>
      {error && <div style={{ background: "#fee", padding: 10 }}>{error}</div>}

      <form onSubmit={add} style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        <input value={name} onChange={(e)=>setName(e.target.value)} placeholder="Name" required />
        <input style={{ flex: 1 }} value={address} onChange={(e)=>setAddress(e.target.value)} placeholder="Address" required />
        <button>Add</button>
      </form>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
        {locations.map((l) => (
          <div key={l.id} style={{ border: "1px solid #ddd", borderRadius: 10, padding: 12 }}>
            <div style={{ fontWeight: 700 }}>{l.name}</div>
            <div style={{ opacity: 0.7 }}>{l.address}</div>
            <div style={{ fontSize: 12, opacity: 0.5 }}>id: {l.id}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
