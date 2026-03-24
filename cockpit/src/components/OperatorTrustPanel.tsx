import { useState, useEffect, useCallback } from "react";
import {
  fetchOperatorTrust,
  type OperatorTrustCockpitSnapshot,
  type OperatorTrustPosture,
} from "../api/daedalusClient";
import "./OperatorTrustPanel.css";

const POSTURE_LABELS: Record<OperatorTrustPosture, string> = {
  unbound: "Unbound",
  trusted_canonical: "Trusted (Canonical)",
  trusted_uncalibrated: "Trusted (Uncalibrated)",
  cautious: "Cautious",
  hostile_or_unknown: "Hostile / Unknown",
};

const POSTURE_COLORS: Record<OperatorTrustPosture, string> = {
  unbound: "#8b949e",
  trusted_canonical: "#4caf50",
  trusted_uncalibrated: "#66bb6a",
  cautious: "#ffb300",
  hostile_or_unknown: "#f85149",
};

function TrustBar({ label, value }: { label: string; value: number }) {
  const color =
    value >= 80 ? "#4caf50" :
    value >= 50 ? "#ffb300" :
    "#f85149";
  return (
    <div className="trust-bar">
      <span className="trust-bar__label">{label}</span>
      <div className="trust-bar__track">
        <div className="trust-bar__fill" style={{ width: `${value}%`, background: color }} />
      </div>
      <span className="trust-bar__value">{Math.round(value)}</span>
    </div>
  );
}

export function OperatorTrustPanel() {
  const [data, setData] = useState<OperatorTrustCockpitSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const snap = await fetchOperatorTrust();
      setData(snap);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load operator trust");
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 5_000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <section className="operator-trust-panel">
      <h3 className="operator-trust-panel__title">Operator Identity</h3>

      {error && <p className="operator-trust-panel__error">{error}</p>}

      {data && (
        <>
          <div className="operator-trust-panel__header">
            <div className="operator-trust-panel__operator">
              {data.boundOperatorId
                ? <><span className="operator-trust-panel__name">{data.boundOperatorName ?? data.boundOperatorId}</span><span className="operator-trust-panel__id">({data.boundOperatorId})</span></>
                : <span className="operator-trust-panel__unbound">No operator bound</span>}
            </div>
            <div
              className="operator-trust-panel__posture-badge"
              style={{ background: POSTURE_COLORS[data.posture] + "22", color: POSTURE_COLORS[data.posture], borderColor: POSTURE_COLORS[data.posture] + "44" }}
            >
              {POSTURE_LABELS[data.posture]}
            </div>
          </div>

          <div className="operator-trust-panel__score-row">
            <div className="operator-trust-panel__score-ring" style={{ borderColor: POSTURE_COLORS[data.posture] }}>
              <span className="operator-trust-panel__score-number">{data.trustScore}</span>
            </div>
            <div className="operator-trust-panel__score-meta">
              <span className="operator-trust-panel__comfort">{data.comfortPosture === "fluid" ? "Fluid UX" : data.comfortPosture === "careful" ? "Careful UX" : "Normal UX"}</span>
              <span className="operator-trust-panel__calibrated">{data.calibrated ? "Calibrated" : "Not calibrated"}</span>
            </div>
          </div>

          <p className="operator-trust-panel__narrative">{data.narrative}</p>

          <div className="operator-trust-panel__axes">
            <TrustBar label="Credentials" value={data.axes.credentials} />
            <TrustBar label="Device" value={data.axes.deviceGraph} />
            <TrustBar label="Behavior" value={data.axes.behaviorProfile} />
            <TrustBar label="Continuity" value={data.axes.continuity} />
          </div>

          {data.freeze.frozen && (
            <div className="operator-trust-panel__freeze">
              Constitutional Freeze Active: {data.freeze.reason}
            </div>
          )}

          {data.recentHighRiskDecisions.length > 0 && (
            <div className="operator-trust-panel__hr-section">
              <h4>Recent High-Risk Decisions</h4>
              {data.recentHighRiskDecisions.slice().reverse().slice(0, 5).map((d, i) => (
                <div key={i} className={`operator-trust-panel__hr-entry ${d.allowed ? "hr--allowed" : "hr--denied"}`}>
                  <span className="hr__action">{d.action}</span>
                  <span className={`hr__badge ${d.allowed ? "hr__badge--allowed" : "hr__badge--denied"}`}>
                    {d.allowed ? "ALLOWED" : "DENIED"}
                  </span>
                  {d.reasons.length > 0 && <span className="hr__reasons">{d.reasons.join(", ")}</span>}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!data && !error && <p className="operator-trust-panel__muted">Loading...</p>}
    </section>
  );
}
