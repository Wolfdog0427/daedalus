import { useStrategy } from "../hooks/useStrategy";
import { useTelemetry } from "../hooks/useTelemetry";
import type { AlignmentBreakdown, StrategyName } from "../api/daedalusClient";
import { AlignmentMeter } from "./AlignmentMeter";
import { AlignmentTimeline } from "./AlignmentTimeline";
import { AlignmentHeatmap } from "./AlignmentHeatmap";
import "./StrategyPanel.css";

const STRATEGY_LABELS: Record<StrategyName, string> = {
  sovereignty_stable: "Sovereignty Stable",
  sovereignty_contested: "Sovereignty Contested",
  identity_reinforcement: "Identity Reinforcement",
  governance_attentive: "Governance Attentive",
  governance_undercorrection: "Governance Undercorrection",
  stability_recovery: "Stability Recovery",
  alignment_nominal: "Alignment Nominal",
  alignment_degraded: "Alignment Degraded",
  alignment_guard_critical: "Guard: Critical",
  alignment_guard_cautious: "Guard: Cautious",
  autonomy_paused_alignment_critical: "Autonomy Paused",
};

const AXIS_LABELS: Record<keyof AlignmentBreakdown, string> = {
  sovereignty: "Sovereignty",
  identity: "Identity",
  governance: "Governance",
  stability: "Stability",
};

const AXIS_ICONS: Record<keyof AlignmentBreakdown, string> = {
  sovereignty: "S",
  identity: "I",
  governance: "G",
  stability: "T",
};

function alignmentTier(score: number): "critical" | "low" | "moderate" | "strong" | "excellent" {
  if (score < 25) return "critical";
  if (score < 45) return "low";
  if (score < 65) return "moderate";
  if (score < 80) return "strong";
  return "excellent";
}

function strategyTone(name: StrategyName): string {
  if (name === "sovereignty_stable" || name === "alignment_nominal") return "healthy";
  if (name === "governance_attentive" || name === "identity_reinforcement") return "attentive";
  if (name === "sovereignty_contested" || name === "governance_undercorrection") return "warning";
  if (name === "alignment_guard_cautious" || name === "stability_recovery" || name === "alignment_degraded") return "warning";
  if (name === "alignment_guard_critical" || name === "autonomy_paused_alignment_critical") return "critical";
  return "critical";
}

function AxisBar({ axis, value, isWeakest, isStrongest }: {
  axis: keyof AlignmentBreakdown;
  value: number;
  isWeakest: boolean;
  isStrongest: boolean;
}) {
  const tier = alignmentTier(value);
  return (
    <div className={`strategy-axis ${isWeakest ? "strategy-axis--weakest" : ""} ${isStrongest ? "strategy-axis--strongest" : ""}`}>
      <div className="strategy-axis-head">
        <span className="strategy-axis-icon">{AXIS_ICONS[axis]}</span>
        <span className="strategy-axis-label">{AXIS_LABELS[axis]}</span>
        <span className={`strategy-axis-value strategy-axis-value--${tier}`}>{value}%</span>
      </div>
      <div className="strategy-axis-track">
        <div
          className={`strategy-axis-fill strategy-axis-fill--${tier}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

export function StrategyPanel() {
  const { evaluation, error, loading } = useStrategy();
  const { telemetry } = useTelemetry();

  return (
    <section className="strategy-panel">
      <div className="strategy-panel__header">
        <h2 className="strategy-panel__title">Strategy Alignment</h2>
        {evaluation && (
          <div className="strategy-panel__badges">
            <span className={`strategy-panel__badge strategy-panel__badge--${strategyTone(evaluation.name)}`}>
              {STRATEGY_LABELS[evaluation.name] ?? evaluation.name}
            </span>
            {evaluation.gated && (
              <span className="strategy-panel__badge strategy-panel__badge--gated">GATED</span>
            )}
            {evaluation.selfCorrected && (
              <span className="strategy-panel__badge strategy-panel__badge--corrected">SELF-CORRECTED</span>
            )}
            {evaluation.escalation && evaluation.escalation.level !== "none" && (
              <span className={`strategy-panel__badge strategy-panel__badge--escalation-${evaluation.escalation.level}`}>
                ESC: {evaluation.escalation.level.toUpperCase()}
              </span>
            )}
            {evaluation.safeMode?.active && (
              <span className="strategy-panel__badge strategy-panel__badge--safe-mode">SAFE MODE</span>
            )}
          </div>
        )}
      </div>

      {loading && !evaluation && <p className="strategy-panel__muted">Evaluating...</p>}
      {error && <p className="strategy-panel__error">{error}</p>}

      {evaluation && (
        <>
          {evaluation.safeMode?.active && (
            <div className="strategy-safe-mode-banner">
              <span className="strategy-safe-mode-banner__icon">!</span>
              <span className="strategy-safe-mode-banner__text">
                Constitutional Safe Mode active{evaluation.safeMode.reason ? `: ${evaluation.safeMode.reason}` : ""}
                {evaluation.safeMode.since && (
                  <> since {new Date(evaluation.safeMode.since).toLocaleTimeString()}</>
                )}
              </span>
            </div>
          )}

          {evaluation.escalation && evaluation.escalation.level === "critical" && (
            <div className="strategy-escalation-banner strategy-escalation-banner--critical">
              <span className="strategy-escalation-banner__icon">!!</span>
              <span className="strategy-escalation-banner__text">
                Critical escalation: autonomy paused.
                {evaluation.escalation.reason && <> {evaluation.escalation.reason}</>}
              </span>
            </div>
          )}

          <div className="strategy-composite">
            <div className="strategy-composite__ring">
              <svg viewBox="0 0 36 36" className="strategy-ring-svg">
                <path
                  className="strategy-ring-bg"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className={`strategy-ring-fill strategy-ring-fill--${alignmentTier(evaluation.alignment)}`}
                  strokeDasharray={`${evaluation.alignment}, 100`}
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <div className="strategy-composite__score">
                <span className="strategy-composite__number">{evaluation.alignment}</span>
                <span className="strategy-composite__percent">%</span>
              </div>
            </div>
            <div className="strategy-composite__meta">
              <div className="strategy-composite__confidence">
                Confidence: <strong>{evaluation.confidence}%</strong>
              </div>
              {telemetry?.systemConfidence && (
                <div className="strategy-composite__sys-confidence" title={`Stability: ${telemetry.systemConfidence.stabilityBonus}% · Trajectory: ${telemetry.systemConfidence.trajectoryBonus}%`}>
                  System: <strong>{telemetry.systemConfidence.score}%</strong>
                  <span className="strategy-composite__sys-bias">
                    {telemetry.systemConfidence.approvalBias > 0 ? ` (+${telemetry.systemConfidence.approvalBias})` :
                     telemetry.systemConfidence.approvalBias < 0 ? ` (${telemetry.systemConfidence.approvalBias})` : ""}
                  </span>
                </div>
              )}
              <div className="strategy-composite__evaluated">
                {new Date(evaluation.evaluatedAt).toLocaleTimeString()}
              </div>
              {evaluation.posture && (
                <div className="strategy-composite__posture">
                  Resp: {(evaluation.posture.responsiveness * 100).toFixed(0)}%
                  &nbsp;·&nbsp;
                  Caut: {(evaluation.posture.caution * 100).toFixed(0)}%
                </div>
              )}
            </div>
          </div>

          {evaluation.drift?.drifting && (
            <div className="strategy-drift-warning">
              <span className="strategy-drift-warning__icon">↓</span>
              <span className="strategy-drift-warning__text">
                Alignment drift detected: {evaluation.drift.delta > 0 ? "+" : ""}{evaluation.drift.delta.toFixed(1)}pt
                over {evaluation.drift.window} evaluations
              </span>
            </div>
          )}

          <div className="strategy-axes">
            {(["sovereignty", "identity", "governance", "stability"] as const).map(axis => (
              <AxisBar
                key={axis}
                axis={axis}
                value={evaluation.alignmentBreakdown[axis]}
                isWeakest={evaluation.weakestAxis === axis}
                isStrongest={evaluation.strongestAxis === axis}
              />
            ))}
          </div>

          <div className="strategy-alignment-meter">
            <AlignmentMeter value={evaluation.alignment} label="Composite" />
          </div>

          {telemetry && (
            <>
              <AlignmentTimeline history={telemetry.alignmentHistory} />
              <AlignmentHeatmap history={telemetry.alignmentHistory} />
            </>
          )}

          {evaluation.notes && (
            <div className="strategy-notes">
              <span className="strategy-notes__icon">i</span>
              <span className="strategy-notes__text">{evaluation.notes}</span>
            </div>
          )}
        </>
      )}
    </section>
  );
}
