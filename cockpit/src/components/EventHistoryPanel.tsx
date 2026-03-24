import React, { useEffect, useState, useCallback } from "react";
import { fetchEventHistory } from "../api/daedalusClient";

const TYPE_COLORS: Record<string, string> = {
  POSTURE_CHANGED: "#ff9800",
  GOVERNANCE_OVERRIDE_APPLIED: "#f44336",
  CONTINUITY_DRIFT_DETECTED: "#e91e63",
  MIRROR_NODE_JOINED: "#4caf50",
  MIRROR_NODE_DETACHED: "#9e9e9e",
  MIRROR_NODE_QUARANTINED: "#f44336",
  MIRROR_NODE_ERROR: "#ff5722",
  MIRROR_NODE_STALE: "#795548",
  BEING_PRESENCE_UPDATED: "#2196f3",
};

export function EventHistoryPanel() {
  const [events, setEvents] = useState<any[]>([]);
  const [filter, setFilter] = useState("");

  const refresh = useCallback(async () => {
    try {
      setEvents(await fetchEventHistory(200, filter || undefined));
    } catch { /* ignore */ }
  }, [filter]);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 3000);
    return () => clearInterval(iv);
  }, [refresh]);

  const governanceTypes = [
    "", "POSTURE_CHANGED", "GOVERNANCE_OVERRIDE_APPLIED", "CONTINUITY_DRIFT_DETECTED",
    "MIRROR_NODE_JOINED", "MIRROR_NODE_DETACHED", "MIRROR_NODE_QUARANTINED",
    "MIRROR_NODE_ERROR", "MIRROR_NODE_STALE", "BEING_PRESENCE_UPDATED",
  ];

  return (
    <div style={{ border: "1px solid #333", borderRadius: 8, padding: 16, margin: "8px 0", background: "#1a1a2e" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <h3 style={{ margin: 0, color: "#e0e0e0" }}>Event History</h3>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #555", background: "#2a2a3e", color: "#e0e0e0", fontSize: 12 }}
        >
          {governanceTypes.map((t) => (
            <option key={t} value={t}>{t || "All types"}</option>
          ))}
        </select>
        <span style={{ color: "#888", fontSize: 12 }}>{events.length} events</span>
      </div>

      <div style={{ maxHeight: 300, overflowY: "auto" }}>
        {events.length === 0 && <p style={{ color: "#666", fontStyle: "italic" }}>No events yet</p>}
        {[...events].reverse().slice(0, 100).map((evt, i) => (
          <div key={i} style={{ display: "flex", gap: 8, padding: "4px 8px", fontSize: 12, borderBottom: "1px solid #252540" }}>
            <span style={{ color: "#666", width: 75, flexShrink: 0 }}>
              {new Date(evt.timestamp).toLocaleTimeString()}
            </span>
            <span style={{ color: TYPE_COLORS[evt.type] ?? "#aaa", fontWeight: 600, width: 200, flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {evt.type}
            </span>
            <span style={{ color: "#ccc", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {evt.summary ?? evt.nodeId ?? ""}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
