import { useState, useEffect, useCallback } from "react";
import {
  fetchRegulation,
  type RegulationResponse,
  type RegulationOutput,
  type DriftMetrics,
} from "../api/daedalusClient";
import "./RegulationPanel.css";

function DriftMetricsDisplay({ metrics }: { metrics: DriftMetrics }) {
  const magnitudeColor =
    metrics.magnitude <= 5 ? "drift--low" :
    metrics.magnitude <= 15 ? "drift--medium" : "drift--high";

  const slopeArrow = metrics.slope > 0.1 ? "↑" : metrics.slope < -0.1 ? "↓" : "→";
  const accelArrow = metrics.acceleration > 0.1 ? "⇈" : metrics.acceleration < -0.1 ? "⇊" : "—";

  return (
    <div className="regulation-drift">
      <div className={`regulation-drift__cell ${magnitudeColor}`}>
        <span className="regulation-drift__label">Magnitude</span>
        <span className="regulation-drift__value">{metrics.magnitude.toFixed(1)}</span>
      </div>
      <div className="regulation-drift__cell">
        <span className="regulation-drift__label">Slope {slopeArrow}</span>
        <span className="regulation-drift__value">{metrics.slope.toFixed(3)}</span>
      </div>
      <div className="regulation-drift__cell">
        <span className="regulation-drift__label">Accel {accelArrow}</span>
        <span className="regulation-drift__value">{metrics.acceleration.toFixed(3)}</span>
      </div>
    </div>
  );
}

function AdjustmentBar({ label, value, max, tier }: { label: string; value: number; max: number; tier: "micro" | "macro" }) {
  const pct = Math.min(100, (Math.abs(value) / max) * 100);
  const direction = value > 0 ? "positive" : value < 0 ? "negative" : "neutral";
  return (
    <div className={`regulation-bar regulation-bar--${tier}`}>
      <span className="regulation-bar__label">{label}</span>
      <div className="regulation-bar__track">
        <div
          className={`regulation-bar__fill regulation-bar__fill--${direction}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="regulation-bar__value">{value.toFixed(3)}</span>
    </div>
  );
}

function GovernanceSignals({ output }: { output: RegulationOutput }) {
  const signals = [
    { active: output.shouldEnterSafeMode, label: "Enter Safe Mode", severity: "critical" },
    { active: output.shouldPauseAutonomy, label: "Pause Autonomy", severity: "high" },
    { active: output.shouldExitSafeMode, label: "Exit Safe Mode", severity: "recovery" },
    { active: output.shouldResumeAutonomy, label: "Resume Autonomy", severity: "recovery" },
  ].filter(s => s.active);

  if (signals.length === 0) return null;

  return (
    <div className="regulation-signals">
      {signals.map(s => (
        <span key={s.label} className={`regulation-signal regulation-signal--${s.severity}`}>
          {s.label}
        </span>
      ))}
    </div>
  );
}

export function RegulationPanel() {
  const [data, setData] = useState<RegulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const resp = await fetchRegulation();
      setData(resp);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load regulation");
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 5_000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <section className="regulation-panel">
      <h3 className="regulation-panel__title">Alignment Regulation</h3>

      {error && <p className="regulation-panel__error">{error}</p>}

      {data && (
        <>
          <div className="regulation-panel__config">
            <span>Target: {data.config.targetAlignment}%</span>
            <span>Floor: {data.config.floorAlignment}%</span>
            <span>μ-gain: {data.config.microGain}</span>
            <span>M-gain: {data.config.macroGain}</span>
            <span>Damping: {data.config.macroDamping}</span>
          </div>

          {data.lastOutput ? (
            <div className="regulation-panel__output">
              <DriftMetricsDisplay metrics={data.lastOutput.driftMetrics} />

              <div className="regulation-panel__adjustments">
                <AdjustmentBar label="Micro" value={data.lastOutput.microAdjustment} max={2} tier="micro" />
                <AdjustmentBar label="Macro" value={data.lastOutput.macroAdjustment} max={15} tier="macro" />
              </div>

              {data.lastOutput.telemetry.appliedMacro && (
                <div className="regulation-panel__macro-detail">
                  <span className="regulation-panel__reason">{data.lastOutput.telemetry.reason}</span>
                  <span className="regulation-panel__raw">
                    raw: {data.lastOutput.telemetry.macroRawCorrection.toFixed(2)} →
                    damped: {data.lastOutput.telemetry.macroDampedCorrection.toFixed(2)}
                  </span>
                </div>
              )}

              <GovernanceSignals output={data.lastOutput} />
            </div>
          ) : (
            <p className="regulation-panel__muted">No regulation output yet</p>
          )}
        </>
      )}

      {!data && !error && <p className="regulation-panel__muted">Loading...</p>}
    </section>
  );
}
