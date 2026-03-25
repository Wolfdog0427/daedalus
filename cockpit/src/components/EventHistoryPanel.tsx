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
  NEGOTIATION_COMPLETED: "#9c27b0",
  STRATEGY_CHANGED: "#00bcd4",
  ALIGNMENT_ESCALATION: "#ff1744",
  SAFE_MODE_ACTIVE: "#d50000",
  ALIGNMENT_CONFIG_CHANGED: "#7c4dff",
  CHANGE_AUTO_APPROVED: "#66bb6a",
  CHANGE_REQUIRES_REVIEW: "#ffa726",
  REGULATION_MACRO_FIRED: "#ff6d00",
  REGULATION_SAFE_MODE_SIGNAL: "#d50000",
  CHANGE_REGISTERED: "#42a5f5",
  CHANGE_ROLLED_BACK: "#ef5350",
  CHANGE_ACCEPTED: "#66bb6a",
  OPERATOR_BOUND: "#4caf50",
  OPERATOR_UNBOUND: "#ff9800",
  OPERATOR_TRUST_SUSPICIOUS: "#f44336",
  OPERATOR_HIGH_RISK_DENIED: "#d50000",
  CONSTITUTIONAL_FREEZE_CHANGED: "#7c4dff",
  MIRROR_NODE_HEARTBEAT: "#81c784",
  MIRROR_NODE_CAP_SYNCED: "#4db6ac",
  MIRROR_NODE_EXPRESSIVE_SYNCED: "#4dd0e1",
  MIRROR_NODE_PROFILE_SYNCED: "#4fc3f7",
  OPERATOR_CHAT_MESSAGE: "#26c6da",
  DAEDALUS_PROPOSAL_CREATED: "#ab47bc",
  DAEDALUS_PROPOSAL_APPROVED: "#66bb6a",
  DAEDALUS_PROPOSAL_APPLIED: "#4caf50",
  DAEDALUS_PROPOSAL_DENIED: "#ef5350",
};

export function EventHistoryPanel() {
  const [events, setEvents] = useState<any[]>([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setEvents(await fetchEventHistory(200, filter || undefined));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load events");
    }
  }, [filter]);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 3000);
    return () => clearInterval(iv);
  }, [refresh]);

  const allEventTypes = [
    "",
    "STRATEGY_CHANGED", "ALIGNMENT_ESCALATION", "SAFE_MODE_ACTIVE", "ALIGNMENT_CONFIG_CHANGED",
    "POSTURE_CHANGED", "GOVERNANCE_OVERRIDE_APPLIED", "CONTINUITY_DRIFT_DETECTED",
    "REGULATION_MACRO_FIRED", "REGULATION_SAFE_MODE_SIGNAL",
    "CHANGE_AUTO_APPROVED", "CHANGE_REQUIRES_REVIEW", "CHANGE_REGISTERED", "CHANGE_ROLLED_BACK", "CHANGE_ACCEPTED",
    "DAEDALUS_PROPOSAL_CREATED", "DAEDALUS_PROPOSAL_APPROVED", "DAEDALUS_PROPOSAL_APPLIED", "DAEDALUS_PROPOSAL_DENIED",
    "OPERATOR_BOUND", "OPERATOR_UNBOUND", "OPERATOR_TRUST_SUSPICIOUS", "OPERATOR_HIGH_RISK_DENIED", "CONSTITUTIONAL_FREEZE_CHANGED",
    "OPERATOR_CHAT_MESSAGE",
    "MIRROR_NODE_JOINED", "MIRROR_NODE_DETACHED", "MIRROR_NODE_QUARANTINED", "MIRROR_NODE_HEARTBEAT",
    "MIRROR_NODE_ERROR", "MIRROR_NODE_STALE", "MIRROR_NODE_CAP_SYNCED", "MIRROR_NODE_EXPRESSIVE_SYNCED", "MIRROR_NODE_PROFILE_SYNCED",
    "BEING_PRESENCE_UPDATED", "NEGOTIATION_COMPLETED",
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
          {allEventTypes.map((t) => (
            <option key={t} value={t}>{t || "All types"}</option>
          ))}
        </select>
        <span style={{ color: "#888", fontSize: 12 }}>{events.length} events</span>
      </div>

      {error && <p style={{ color: "#f85149", fontSize: 12, margin: "4px 0 8px" }}>{error}</p>}

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
