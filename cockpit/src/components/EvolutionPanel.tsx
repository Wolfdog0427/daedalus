import { useState, useEffect, useCallback } from "react";
import {
  fetchApprovalGate,
  submitChangeProposal,
  fetchRollbackRegistry,
  type ApprovalGateResponse,
  type ApprovalDecision,
  type ApprovalReasonBreakdown,
  type ChangeProposalKind,
  type RollbackRegistrySnapshot,
} from "../api/daedalusClient";
import "./EvolutionPanel.css";

const REASON_LABELS: Record<keyof ApprovalReasonBreakdown, string> = {
  alignmentOK: "Alignment",
  confidenceOK: "Confidence",
  impactOK: "Impact",
  invariantsOK: "Invariants",
  reversibleOK: "Reversible",
  safeModeOK: "Safe Mode",
  cooldownOK: "Cooldown",
};

const PROPOSAL_KINDS: { value: ChangeProposalKind; label: string }[] = [
  { value: "alignment_config", label: "Alignment Config" },
  { value: "kernel_config", label: "Kernel Config" },
  { value: "strategy_override", label: "Strategy Override" },
  { value: "governance_policy", label: "Governance Policy" },
  { value: "regulation_tuning", label: "Regulation Tuning" },
  { value: "posture_shift", label: "Posture Shift" },
  { value: "node_authority", label: "Node Authority" },
  { value: "identity_update", label: "Identity Update" },
  { value: "telemetry_config", label: "Telemetry Config" },
  { value: "other", label: "Other" },
];

function ReasonBadge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span className={`evolution-reason ${ok ? "evolution-reason--pass" : "evolution-reason--fail"}`}>
      {ok ? "✓" : "×"} {label}
    </span>
  );
}

function DecisionCard({ decision }: { decision: ApprovalDecision }) {
  const time = new Date(decision.decidedAt).toLocaleTimeString();
  const approved = decision.autoApprove;

  return (
    <div className={`evolution-decision ${approved ? "evolution-decision--approved" : "evolution-decision--review"}`}>
      <div className="evolution-decision__top">
        <span className={`evolution-decision__verdict ${approved ? "verdict--approved" : "verdict--needs-review"}`}>
          {approved ? "Auto-Approved" : "Needs Review"}
        </span>
        <span className="evolution-decision__time">{time}</span>
      </div>
      <div className="evolution-decision__desc">{decision.proposal.description}</div>
      <div className="evolution-decision__meta">
        <span className="evolution-decision__kind">{decision.proposal.kind}</span>
        <span className={`evolution-decision__impact evolution-decision__impact--${decision.derivedImpact}`}>
          {decision.derivedImpact.toUpperCase()}
        </span>
        <span className="evolution-decision__score">A:{decision.alignment}% C:{decision.confidence}%</span>
      </div>
      <div className="evolution-decision__reasons">
        {(Object.entries(decision.reasons) as [keyof ApprovalReasonBreakdown, boolean][]).map(([key, ok]) => (
          <ReasonBadge key={key} label={REASON_LABELS[key]} ok={ok} />
        ))}
      </div>
    </div>
  );
}

export function EvolutionPanel() {
  const [gate, setGate] = useState<ApprovalGateResponse | null>(null);
  const [rollback, setRollback] = useState<RollbackRegistrySnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [kind, setKind] = useState<ChangeProposalKind>("alignment_config");
  const [description, setDescription] = useState("");
  const [submitResult, setSubmitResult] = useState<ApprovalDecision | null>(null);

  const load = useCallback(async () => {
    try {
      const [g, r] = await Promise.all([fetchApprovalGate(), fetchRollbackRegistry()]);
      setGate(g);
      setRollback(r);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load evolution data");
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 8_000);
    return () => clearInterval(id);
  }, [load]);

  const handleSubmit = useCallback(async () => {
    if (!description.trim() || submitting) return;
    setSubmitting(true);
    setSubmitResult(null);
    try {
      const result = await submitChangeProposal({ kind, description: description.trim() });
      setSubmitResult(result);
      setDescription("");
      void load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Proposal submission failed");
    } finally {
      setSubmitting(false);
    }
  }, [kind, description, submitting, load]);

  const pendingCount = rollback ? rollback.activeChanges.length : 0;
  const decisions = gate?.recentDecisions ?? [];
  const needsReview = decisions.filter(d => !d.autoApprove).length;

  return (
    <section className="evolution-panel">
      <div className="evolution-panel__header">
        <h3 className="evolution-panel__title">
          <span className="evolution-panel__icon">◈</span>
          Evolution Proposals
        </h3>
        {needsReview > 0 ? (
          <span className="evolution-panel__badge evolution-panel__badge--pending">
            {needsReview} awaiting review
          </span>
        ) : (
          <span className="evolution-panel__badge evolution-panel__badge--clear">
            All clear
          </span>
        )}
      </div>

      {error && <div className="evolution-error">{error}</div>}

      {gate && (
        <div className="evolution-gate">
          <div className="evolution-gate__item">
            Alignment ≥ <span className="evolution-gate__val">{gate.config.alignmentThreshold}%</span>
          </div>
          <div className="evolution-gate__item">
            Confidence ≥ <span className="evolution-gate__val">{gate.config.confidenceThreshold}%</span>
          </div>
          <div className="evolution-gate__item">
            Cooldown: <span className="evolution-gate__val">{gate.config.cooldownMs}ms</span>
          </div>
          <div className="evolution-gate__item">
            Safe mode: <span className="evolution-gate__val">{gate.config.allowDuringSafeMode ? "allowed" : "blocked"}</span>
          </div>
        </div>
      )}

      <div className="evolution-form">
        <div className="evolution-form__row">
          <select
            className="evolution-form__select"
            value={kind}
            onChange={(e) => setKind(e.target.value as ChangeProposalKind)}
          >
            {PROPOSAL_KINDS.map((pk) => (
              <option key={pk.value} value={pk.value}>{pk.label}</option>
            ))}
          </select>
          <input
            className="evolution-form__input"
            type="text"
            placeholder="Describe the proposed evolution..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          />
        </div>
        <button
          className="evolution-form__submit"
          onClick={handleSubmit}
          disabled={!description.trim() || submitting}
        >
          {submitting ? "Evaluating..." : "Submit Proposal"}
        </button>
      </div>

      {submitResult && (
        <DecisionCard decision={submitResult} />
      )}

      {rollback && (
        <div className="evolution-rollback">
          <div className="evolution-rollback__title">Change Registry</div>
          <div className="evolution-rollback__stats">
            <span className="evolution-rollback__stat">
              Active: <span className="evolution-rollback__num">{rollback.activeChanges.length}</span>
            </span>
            <span className="evolution-rollback__stat">
              Accepted: <span className="evolution-rollback__num">{rollback.acceptedCount}</span>
            </span>
            <span className="evolution-rollback__stat">
              Rolled back: <span className="evolution-rollback__num">{rollback.rolledBackCount}</span>
            </span>
          </div>
        </div>
      )}

      {decisions.length > 0 ? (
        <div className="evolution-decisions">
          {decisions.slice().reverse().slice(0, 12).map((d, i) => (
            <DecisionCard key={d.proposal.id ?? `d-${i}`} decision={d} />
          ))}
        </div>
      ) : (
        <div className="evolution-empty">No proposals evaluated yet. Submit one above to begin.</div>
      )}
    </section>
  );
}
