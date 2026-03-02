/**
 * Locations page
 *
 * Purpose:
 * - CRUD-ish UI for saved locations (name + address)
 * - Locations are used as origin/destination inputs elsewhere (e.g., Analyze)
 *
 * Notes:
 * - This page assumes the backend geocodes/stores lat/lng (if needed) when creating a location.
 * - Deletion uses the built-in confirm() dialog and optimistically updates local state on success.
 */

import { useEffect, useState } from "react";
import { api } from "../api";
import { Alert, Field, PageHeader } from "../components/ui";

export default function Locations() {
  // Current list of saved locations
  const [locations, setLocations] = useState([]);

  // Controlled inputs for "Add location" form
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");

  // UI state
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  /**
   * refresh()
   * Pulls the latest locations from the backend and updates UI state.
   * Centralizing this avoids duplicating fetch + error handling across handlers.
   */
  async function refresh() {
    setError("");
    try {
      setLocations(await api.listLocations());
    } catch (e) {
      setError(String(e?.message || e));
    }
  }

  // Initial load on mount
  useEffect(() => {
    refresh();
  }, []);

  /**
   * add()
   * Form submit handler to create a new location, then re-fetch list.
   * Uses saving flag to disable the submit button and show progress.
   */
  async function add(e) {
    e.preventDefault();
    setError("");
    setSaving(true);

    try {
      await api.createLocation({ name, address });

      // Reset form inputs after successful create
      setName("");
      setAddress("");

      // Re-fetch to keep UI consistent with backend source-of-truth
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
        right={
          // Convenience: scroll to the add form instead of forcing the user to hunt for it
          <button
            className="btn btnPrimary"
            onClick={() =>
              document
                .getElementById("addLocForm")
                ?.scrollIntoView({ behavior: "smooth" })
            }
          >
            ＋ Add Location
          </button>
        }
      />

      {/* Global error banner */}
      {error && <Alert>{error}</Alert>}

      {/* Add location form section */}
      <div id="addLocForm" className="panel panelPad" style={{ marginTop: 14 }}>
        <div className="sectionTitle">Add a Location</div>

        <form onSubmit={add}>
          <div className="formRow">
            <Field label="Name">
              <input
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Home, Office, Gym…"
                required
              />
            </Field>

            <Field label="Address">
              <input
                className="input"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="123 Maple St, City, ST"
                required
              />
            </Field>
          </div>

          {/* Form actions */}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              marginTop: 10,
              gap: 10,
            }}
          >
            {/* Client-side reset only (does not touch backend) */}
            <button
              type="button"
              className="btn"
              onClick={() => {
                setName("");
                setAddress("");
              }}
            >
              Clear
            </button>

            {/* Submit button disabled while API request is in flight */}
            <button className="btn btnPrimary" disabled={saving}>
              {saving ? "Saving…" : "Save Location"}
            </button>
          </div>
        </form>
      </div>

      {/* Locations grid/list */}
      <div className="locGrid">
        {locations.map((l) => (
          <div key={l.id} className="panel locCard">
            <div>
              <p className="locName">{l.name}</p>
              <p className="locAddr">{l.address}</p>

              {/* Showing the internal ID can be useful for debugging / referencing */}
              <div style={{ marginTop: 8 }}>
                <span className="badge">ID {l.id}</span>
              </div>

              <button
                className="btn btnDanger"
                onClick={async () => {
                  // Guard: confirm destructive action
                  if (!confirm(`Delete "${l.name}"?`)) return;

                  try {
                    await api.deleteLocation(l.id);

                    // Local state update to remove the deleted item without refetching
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

        {/* Empty state */}
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