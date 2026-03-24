import { useState, useEffect, useCallback } from "react";
import {
  fetchRollbackRegistry,
  type RollbackRegistrySnapshot,
  type AppliedChangeRecord,
  type RollbackEvent,
} from "../api/daedalusClient";
import "./ChangeRegistryPanel.css";

function ChangeRow({ change }: { change: AppliedChangeRecord }) {
  const statusClass = `change-status--${change.status}`;
  return (
    <div className={`change-row ${statusClass}`}>
      <div className="change-row__header">
        <span className="change-row__id">{change.id}</span>
        <span className={`change-row__badge change-row__badge--${change.impact}`}>
          {change.impact.toUpperCase()}
        </span>
        <span className={`change-row__status ${statusClass}`}>
          {change.status}
        </span>
      </div>
      <div className="change-row__desc">{change.description}</div>
      <div className="change-row__meta">
        <span>Tick {change.appliedAtTick}</span>
        <span>Window: {change.evaluationWindow}</span>
        <span>Baseline: {change.baselineAlignment}%</span>
        {change.surfaces.length > 0 && (
          <span className="change-row__surfaces">{change.surfaces.join(", ")}</span>
        )}
      </div>
    </div>
  );
}

function RollbackRow({ event }: { event: RollbackEvent }) {
  return (
    <div className="rollback-row">
      <span className="rollback-row__id">{event.changeId}</span>
      <span className="rollback-row__reason">{event.reason}</span>
      <span className="rollback-row__delta">{event.deltaAlignment.toFixed(1)}%</span>
      <span className="rollback-row__tick">tick {event.rolledBackAt}</span>
    </div>
  );
}

export function ChangeRegistryPanel() {
  const [data, setData] = useState<RollbackRegistrySnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const resp = await fetchRollbackRegistry();
      setData(resp);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load registry");
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 8_000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <section className="change-registry-panel">
      <h3 className="change-registry-panel__title">Change Registry &amp; Rollback</h3>

      {error && <p className="change-registry-panel__error">{error}</p>}

      {data && (
        <>
          <div className="change-registry-panel__stats">
            <span>Active: {data.activeChanges.length}</span>
            <span>Accepted: {data.acceptedCount}</span>
            <span>Rolled back: {data.rolledBackCount}</span>
          </div>

          {data.activeChanges.length > 0 && (
            <div className="change-registry-panel__section">
              <h4>Active Changes</h4>
              {data.activeChanges.map(c => <ChangeRow key={c.id} change={c} />)}
            </div>
          )}

          {data.recentRollbacks.length > 0 && (
            <div className="change-registry-panel__section">
              <h4>Recent Rollbacks</h4>
              {data.recentRollbacks.slice().reverse().slice(0, 8).map((r, i) => (
                <RollbackRow key={`${r.changeId}-${i}`} event={r} />
              ))}
            </div>
          )}

          {data.activeChanges.length === 0 && data.recentRollbacks.length === 0 && (
            <p className="change-registry-panel__muted">No tracked changes</p>
          )}
        </>
      )}

      {!data && !error && <p className="change-registry-panel__muted">Loading...</p>}
    </section>
  );
}
