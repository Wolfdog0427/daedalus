import React, { useEffect, useState, useCallback } from "react";
import { fetchIncidents, openIncident, resolveIncident, type Incident } from "../api/daedalusClient";

const SEVERITY_COLORS: Record<string, string> = {
  LOW: "#4caf50",
  MEDIUM: "#ff9800",
  HIGH: "#f44336",
  CRITICAL: "#b71c1c",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  investigating: "Investigating",
  mitigated: "Mitigated",
  resolved: "Resolved",
};

export function IncidentPanel() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState("MEDIUM");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setIncidents(await fetchIncidents());
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 5000);
    return () => clearInterval(iv);
  }, [refresh]);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setLoading(true);
    try {
      await openIncident({ title: title.trim(), notes: notes.trim() || undefined, severity });
      setTitle("");
      setNotes("");
      await refresh();
    } catch { /* ignore */ }
    setLoading(false);
  };

  const handleResolve = async (id: string) => {
    try {
      await resolveIncident(id);
      await refresh();
    } catch { /* ignore */ }
  };

  const open = incidents.filter((i) => i.status !== "resolved");
  const resolved = incidents.filter((i) => i.status === "resolved");

  return (
    <div style={{ border: "1px solid #333", borderRadius: 8, padding: 16, margin: "8px 0", background: "#1a1a2e" }}>
      <h3 style={{ margin: "0 0 12px", color: "#e0e0e0" }}>Incidents</h3>

      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Incident title..."
          style={{ flex: 1, minWidth: 200, padding: "6px 10px", borderRadius: 4, border: "1px solid #555", background: "#2a2a3e", color: "#e0e0e0" }}
        />
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 4, border: "1px solid #555", background: "#2a2a3e", color: "#e0e0e0" }}
        >
          <option value="LOW">LOW</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="HIGH">HIGH</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
        <button
          onClick={handleCreate}
          disabled={loading || !title.trim()}
          style={{ padding: "6px 16px", borderRadius: 4, background: "#f44336", color: "#fff", border: "none", cursor: "pointer", opacity: loading ? 0.6 : 1 }}
        >
          Open Incident
        </button>
      </div>

      {open.length === 0 && <p style={{ color: "#888", fontStyle: "italic" }}>No active incidents</p>}

      {open.map((inc) => (
        <div key={inc.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 10px", marginBottom: 6, borderRadius: 6, background: "#252540", border: `1px solid ${SEVERITY_COLORS[inc.severity] ?? "#555"}` }}>
          <span style={{ color: SEVERITY_COLORS[inc.severity], fontWeight: 700, fontSize: 12, width: 70, textAlign: "center" }}>{inc.severity}</span>
          <span style={{ flex: 1, color: "#e0e0e0" }}>{inc.title}</span>
          <span style={{ color: "#aaa", fontSize: 12 }}>{STATUS_LABELS[inc.status]}</span>
          <span style={{ color: "#666", fontSize: 11 }}>{new Date(inc.openedAt).toLocaleTimeString()}</span>
          {inc.status !== "resolved" && (
            <button
              onClick={() => handleResolve(inc.id)}
              style={{ padding: "3px 10px", borderRadius: 4, background: "#4caf50", color: "#fff", border: "none", cursor: "pointer", fontSize: 12 }}
            >
              Resolve
            </button>
          )}
        </div>
      ))}

      {resolved.length > 0 && (
        <details style={{ marginTop: 8, color: "#888" }}>
          <summary style={{ cursor: "pointer", fontSize: 13 }}>Resolved ({resolved.length})</summary>
          {resolved.map((inc) => (
            <div key={inc.id} style={{ padding: "4px 10px", fontSize: 12, color: "#666" }}>
              {inc.title} — resolved {inc.closedAt ? new Date(inc.closedAt).toLocaleTimeString() : ""}
            </div>
          ))}
        </details>
      )}
    </div>
  );
}
