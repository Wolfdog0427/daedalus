import { useEffect, useState, useCallback } from "react";
import { fetchOverrides, fetchDrifts } from "../api/daedalusClient";
import { useDaedalusEvents } from "../hooks/useDaedalusEvents";
import type { GovernanceOverride, ContinuityDrift } from "../shared/daedalus/contracts";
import "./GovernancePanel.css";

export function GovernancePanel() {
  const [overrides, setOverrides] = useState<GovernanceOverride[]>([]);
  const [drifts, setDrifts] = useState<ContinuityDrift[]>([]);
  const [error, setError] = useState<string>();

  const loadOverrides = useCallback(() => {
    fetchOverrides().then(setOverrides).catch((e) => setError(e.message));
  }, []);

  const loadDrifts = useCallback(() => {
    fetchDrifts().then(setDrifts).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    loadOverrides();
    loadDrifts();
  }, [loadOverrides, loadDrifts]);

  useDaedalusEvents((event) => {
    if (event.type === "GOVERNANCE_OVERRIDE_APPLIED") loadOverrides();
    if (event.type === "CONTINUITY_DRIFT_DETECTED") loadDrifts();
  });

  return (
    <div className="panel governance-panel">
      <div className="panel-title">Governance</div>
      {error && <div className="error-msg">{error}</div>}

      <h4>Overrides</h4>
      {overrides.length === 0 && <p className="empty">No active overrides</p>}
      {overrides.map((o) => (
        <div key={o.id} className="gov-row">
          <span className={`badge badge-${o.effect.toLowerCase()}`}>{o.effect}</span>
          <span className="gov-scope">{o.scope}</span>
          <span className="gov-reason">{o.reason}</span>
          <span className="gov-by">{o.createdBy?.label}</span>
        </div>
      ))}

      <h4>Continuity Drifts</h4>
      {drifts.length === 0 && <p className="empty">No drifts detected</p>}
      {drifts.map((d) => (
        <div key={d.id} className="gov-row">
          <span className={`badge badge-drift-${d.severity.toLowerCase()}`}>{d.severity}</span>
          <span className="gov-reason">{d.summary}</span>
          <span className="gov-time">{new Date(d.detectedAt).toLocaleTimeString()}</span>
        </div>
      ))}
    </div>
  );
}
