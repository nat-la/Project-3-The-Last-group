import { useEffect, useState } from "react";
import { api } from "../api";
import { Alert, Field, PageHeader } from "../components/ui";

export default function Locations() {
  const [locations, setLocations] = useState([]);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setError("");
    try {
      setLocations(await api.listLocations());
    } catch (e) {
      setError(String(e?.message || e));
    }
  }

  useEffect(() => { refresh(); }, []);

  async function add(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await api.createLocation({ name, address });
      setName("");
      setAddress("");
      await refresh();
    } catch (e) {
      setError(String(e?.message || e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page">

      <PageHeader
        title="Saved Locations"
        subtitle="Manage the origins and destinations for your commute analysis."
        right={<button className="btn btnPrimary" onClick={() => document.getElementById("addLocForm")?.scrollIntoView({ behavior: "smooth" })}>＋ Add Location</button>}
      />

      {error && <Alert>{error}</Alert>}

      <div id="addLocForm" className="panel panelPad" style={{ marginTop: 14 }}>
        <div className="sectionTitle">Add a Location</div>
        <form onSubmit={add}>
          <div className="formRow">
            <Field label="Name">
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Home, Office, Gym…" required />
            </Field>
            <Field label="Address">
              <input className="input" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="123 Maple St, City, ST" required />
            </Field>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10, gap: 10 }}>
            <button type="button" className="btn" onClick={() => { setName(""); setAddress(""); }}>
              Clear
            </button>
            <button className="btn btnPrimary" disabled={saving}>
              {saving ? "Saving…" : "Save Location"}
            </button>
          </div>
        </form>
      </div>

      <div className="locGrid">
        {locations.map((l) => (
          <div key={l.id} className="panel locCard">
            <div>
              <p className="locName">{l.name}</p>
              <p className="locAddr">{l.address}</p>
              <div style={{ marginTop: 8 }}>
                <span className="badge">ID {l.id}</span>
              </div>
              <button
                className="btn btnDanger"
                onClick={async () => {
                  if (!confirm(`Delete "${l.name}"?`)) return;
                  try {
                    await api.deleteLocation(l.id);
                    setLocations((prev) => prev.filter((x) => x.id !== l.id));
                  } catch (e) {
                    setError(String(e?.message || e));
                  }
                }}
              >
                Delete
              </button>
            </div>
          </div>
        ))}

        {locations.length === 0 && (
          <div className="panel panelPad">
            <div className="sectionTitle">No locations yet</div>
            <p className="muted">Add your first location to start analyzing commutes.</p>
          </div>
        )}
      </div>
    </div>
  );
}