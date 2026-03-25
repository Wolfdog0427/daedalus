import React, { useEffect, useState, useCallback } from "react";
import { fetchActions, undoAction, type ActionEntry } from "../api/daedalusClient";

const KIND_LABELS: Record<string, string> = {
  CREATE_OVERRIDE: "Created Override",
  REMOVE_OVERRIDE: "Removed Override",
  CLEAR_OVERRIDES: "Cleared Overrides",
  CAST_VOTE: "Cast Vote",
  CLEAR_VOTES: "Cleared Votes",
  RECORD_DRIFT: "Recorded Drift",
  CLEAR_DRIFTS: "Cleared Drifts",
  OPEN_INCIDENT: "Opened Incident",
  UPDATE_INCIDENT: "Updated Incident",
};

export function ActionLogPanel() {
  const [actions, setActions] = useState<ActionEntry[]>([]);
  const [undoing, setUndoing] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setActions(await fetchActions(50));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load actions");
    }
  }, []);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 5000);
    return () => clearInterval(iv);
  }, [refresh]);

  const handleUndo = async (id: number) => {
    setUndoing(id);
    try {
      await undoAction(id);
      setError(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to undo action");
    }
    setUndoing(null);
  };

  return (
    <div style={{ border: "1px solid #333", borderRadius: 8, padding: 16, margin: "8px 0", background: "#1a1a2e" }}>
      <h3 style={{ margin: "0 0 12px", color: "#e0e0e0" }}>Action Log</h3>

      {error && <p style={{ color: "#f85149", fontSize: 12, margin: "0 0 8px" }}>{error}</p>}

      <div style={{ maxHeight: 250, overflowY: "auto" }}>
        {actions.length === 0 && <p style={{ color: "#666", fontStyle: "italic" }}>No actions recorded yet</p>}
        {[...actions].reverse().map((action) => (
          <div
            key={action.id}
            style={{
              display: "flex", alignItems: "center", gap: 8, padding: "6px 8px", fontSize: 12,
              borderBottom: "1px solid #252540", opacity: action.undone ? 0.4 : 1,
            }}
          >
            <span style={{ color: "#666", width: 70, flexShrink: 0 }}>
              {new Date(action.timestamp).toLocaleTimeString()}
            </span>
            <span style={{ color: "#e0e0e0", flex: 1 }}>
              {KIND_LABELS[action.kind] ?? action.kind}
              {action.undone && <span style={{ color: "#f44336", marginLeft: 6 }}>(undone)</span>}
            </span>
            <span style={{ color: "#888", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {action.payload?.reason ?? action.payload?.title ?? action.payload?.id ?? ""}
            </span>
            {action.undoable && !action.undone && (
              <button
                onClick={() => handleUndo(action.id)}
                disabled={undoing === action.id}
                style={{
                  padding: "2px 10px", borderRadius: 4, background: "#ff9800", color: "#fff",
                  border: "none", cursor: "pointer", fontSize: 11, opacity: undoing === action.id ? 0.5 : 1,
                }}
              >
                Undo
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
