import { useState, useEffect, useCallback } from "react";
import {
  fetchApprovalGate,
  type ApprovalGateResponse,
  type ApprovalDecision,
  type ApprovalReasonBreakdown,
} from "../api/daedalusClient";
import "./ApprovalGatePanel.css";

const REASON_LABELS: Record<keyof ApprovalReasonBreakdown, string> = {
  alignmentOK: "Alignment",
  confidenceOK: "Confidence",
  impactOK: "Impact",
  invariantsOK: "Invariants",
  reversibleOK: "Reversible",
  safeModeOK: "Safe Mode",
  cooldownOK: "Cooldown",
};

function ReasonBadge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span className={`approval-reason ${ok ? "approval-reason--pass" : "approval-reason--fail"}`}>
      {ok ? "+" : "×"} {label}
    </span>
  );
}

function DecisionRow({ decision }: { decision: ApprovalDecision }) {
  const time = new Date(decision.decidedAt).toLocaleTimeString();
  return (
    <div className={`approval-decision ${decision.autoApprove ? "approval-decision--approved" : "approval-decision--rejected"}`}>
      <div className="approval-decision__header">
        <span className={`approval-decision__verdict ${decision.autoApprove ? "verdict--approved" : "verdict--review"}`}>
          {decision.autoApprove ? "AUTO-APPROVED" : "NEEDS REVIEW"}
        </span>
        <span className="approval-decision__time">{time}</span>
      </div>
      <div className="approval-decision__desc">{decision.proposal.description}</div>
      <div className="approval-decision__meta">
        <span className="approval-decision__kind">{decision.proposal.kind}</span>
        <span className={`approval-decision__impact approval-decision__impact--${decision.derivedImpact}`}>
          {decision.derivedImpact.toUpperCase()}
        </span>
        <span className="approval-decision__score">A:{decision.alignment}% C:{decision.confidence}%</span>
      </div>
      <div className="approval-decision__reasons">
        {(Object.entries(decision.reasons) as [keyof ApprovalReasonBreakdown, boolean][]).map(([key, ok]) => (
          <ReasonBadge key={key} label={REASON_LABELS[key]} ok={ok} />
        ))}
      </div>
    </div>
  );
}

export function ApprovalGatePanel() {
  const [data, setData] = useState<ApprovalGateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const resp = await fetchApprovalGate();
      setData(resp);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load approval gate");
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 10_000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <section className="approval-gate-panel">
      <h3 className="approval-gate-panel__title">Auto-Approval Gate</h3>

      {error && <p className="approval-gate-panel__error">{error}</p>}

      {data && (
        <>
          <div className="approval-gate-panel__config">
            <span>Alignment &ge; {data.config.alignmentThreshold}%</span>
            <span>Confidence &ge; {data.config.confidenceThreshold}%</span>
            <span>Cooldown: {data.config.cooldownMs}ms</span>
            <span>Safe Mode: {data.config.allowDuringSafeMode ? "allowed" : "blocked"}</span>
          </div>

          <div className="approval-gate-panel__decisions">
            {data.recentDecisions.length === 0 && (
              <p className="approval-gate-panel__muted">No recent proposals</p>
            )}
            {data.recentDecisions.slice().reverse().slice(0, 10).map((d, i) => (
              <DecisionRow key={d.proposal.id ?? i} decision={d} />
            ))}
          </div>
        </>
      )}

      {!data && !error && <p className="approval-gate-panel__muted">Loading...</p>}
    </section>
  );
}
