import React, { useEffect, useState, useCallback } from "react";
import { fetchCockpitSummary, type CockpitSummary } from "../api/daedalusClient";

const URGENCY_STYLES: Record<string, { bg: string; border: string; label: string }> = {
  calm: { bg: "#1a2e1a", border: "#4caf50", label: "CALM" },
  attentive: { bg: "#2e2a1a", border: "#ff9800", label: "ATTENTIVE" },
  elevated: { bg: "#2e1a1a", border: "#f44336", label: "ELEVATED" },
  critical: { bg: "#3e0a0a", border: "#b71c1c", label: "CRITICAL" },
};

export function SummaryPanel() {
  const [summary, setSummary] = useState<CockpitSummary | null>(null);

  const refresh = useCallback(async () => {
    try {
      setSummary(await fetchCockpitSummary());
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 3000);
    return () => clearInterval(iv);
  }, [refresh]);

  if (!summary) return null;

  const urgency = summary.urgency ?? "calm";
  const style = URGENCY_STYLES[urgency] ?? URGENCY_STYLES.calm;

  return (
    <div style={{ border: `2px solid ${style.border}`, borderRadius: 8, padding: 16, margin: "8px 0", background: style.bg }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <h3 style={{ margin: 0, color: "#e0e0e0" }}>System Status</h3>
        <span style={{ padding: "4px 14px", borderRadius: 12, background: style.border, color: "#fff", fontWeight: 700, fontSize: 13, letterSpacing: 1 }}>
          {style.label}
        </span>
      </div>

      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginBottom: 10, fontSize: 14 }}>
        <div style={{ color: "#e0e0e0" }}>
          <strong>{summary.totalNodes}</strong> nodes
        </div>
        <div style={{ color: "#e0e0e0" }}>
          Posture: <strong>{summary.posture ?? "—"}</strong>
        </div>
        <div style={{ color: summary.totalErrors > 10 ? "#f44336" : "#e0e0e0" }}>
          Errors: <strong>{summary.totalErrors}</strong>
        </div>
        <div style={{ color: "#aaa" }}>
          Overrides: {summary.activeOverrideCount ?? 0} / Drifts: {summary.activeDriftCount ?? 0}
        </div>
      </div>

      {summary.postureReason && (
        <div style={{ color: "#aaa", fontSize: 12, marginBottom: 8 }}>{summary.postureReason}</div>
      )}

      {(summary.recommendedActions?.length ?? 0) > 0 && (
        <div style={{ borderTop: "1px solid #333", paddingTop: 8, marginTop: 4 }}>
          <div style={{ color: "#ff9800", fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Recommended Actions:</div>
          {summary.recommendedActions!.map((action, i) => (
            <div key={i} style={{ color: "#e0e0e0", fontSize: 12, paddingLeft: 12, marginBottom: 2 }}>
              &bull; {action}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
