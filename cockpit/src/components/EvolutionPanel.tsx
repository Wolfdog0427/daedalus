import { useState, useEffect, useCallback } from "react";
import {
  fetchProposalQueue,
  fetchProposalHistory,
  approveDaedalusProposal,
  denyDaedalusProposal,
  fetchApprovalGate,
  submitChangeProposal,
  fetchRollbackRegistry,
  fetchOperatorProposals,
  forceApproveOperatorProposal,
  withdrawOperatorProposal,
  type DaedalusProposal,
  type ProposalParameterChange,
  type ProposalHistoryEntry,
  type ProposalQueueState,
  type OperatorPendingProposal,
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

function ImpactBadge({ impact }: { impact: string }) {
  return (
    <span className={`evo-impact evo-impact--${impact}`}>
      {impact.toUpperCase()}
    </span>
  );
}

const PROPOSAL_KIND_META: Record<string, { label: string; category: "alignment" | "self-improvement" | "capability" }> = {
  alignment_boost: { label: "Alignment", category: "alignment" },
  regulation_tune: { label: "Regulation", category: "alignment" },
  sensitivity_reduction: { label: "Sensitivity", category: "alignment" },
  safe_mode_recovery: { label: "Recovery", category: "alignment" },
  drift_correction: { label: "Drift Fix", category: "alignment" },
  resilience_upgrade: { label: "Resilience", category: "self-improvement" },
  capability_expansion: { label: "Capability", category: "capability" },
  monitoring_enhancement: { label: "Monitoring", category: "self-improvement" },
  architecture_improvement: { label: "Architecture", category: "self-improvement" },
  pattern_learning: { label: "Learning", category: "capability" },
  trust_recovery_protocol: { label: "Trust", category: "self-improvement" },
  fleet_expansion: { label: "Fleet", category: "capability" },
  self_assessment: { label: "Self-Check", category: "self-improvement" },
};

function KindBadge({ kind }: { kind: string }) {
  const meta = PROPOSAL_KIND_META[kind] ?? { label: kind, category: "alignment" as const };
  const catClass = meta.category === "self-improvement" ? "evo-kind--self" : meta.category === "capability" ? "evo-kind--cap" : "evo-kind--align";
  return <span className={`evo-kind ${catClass}`}>{meta.label}</span>;
}

function AlignmentBar({ value, label }: { value: number; label: string }) {
  const color = value >= 85 ? "#3fb950" : value >= 70 ? "#d29922" : "#f85149";
  return (
    <div className="evo-metric">
      <span className="evo-metric__label">{label}</span>
      <div className="evo-metric__bar-bg">
        <div className="evo-metric__bar-fill" style={{ width: `${value}%`, background: color }} />
      </div>
      <span className="evo-metric__val" style={{ color }}>{value}%</span>
    </div>
  );
}

function AxesBadge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span className={`evolution-reason ${ok ? "evolution-reason--pass" : "evolution-reason--fail"}`}>
      {ok ? "✓" : "×"} {label}
    </span>
  );
}

function ConfidenceDimension({ label, value, description }: { label: string; value: number; description: string }) {
  const tier = value >= 75 ? "high" : value >= 50 ? "mid" : "low";
  return (
    <div className={`evo-confidence-dim evo-confidence-dim--${tier}`} title={description}>
      <div className="evo-confidence-dim__bar">
        <div className="evo-confidence-dim__fill" style={{ width: `${value}%` }} />
      </div>
      <div className="evo-confidence-dim__meta">
        <span className="evo-confidence-dim__label">{label}</span>
        <span className="evo-confidence-dim__value">{value}%</span>
      </div>
    </div>
  );
}

/* ── Helpers ────────────────────────────────────────────────────── */

function formatPayloadKey(key: string): string {
  return key
    .replace(/([A-Z])/g, " $1")
    .replace(/_/g, " ")
    .replace(/^\w/, c => c.toUpperCase())
    .trim();
}

function formatPayloadValue(val: unknown): string {
  if (typeof val === "number") return Number.isInteger(val) ? String(val) : val.toFixed(3);
  if (typeof val === "boolean") return val ? "Yes" : "No";
  return String(val);
}

type RecommendationLevel = "safe" | "review" | "caution";

function computeRecommendation(p: DaedalusProposal): { level: RecommendationLevel; label: string; detail: string } {
  if (p.proposalConfidence) {
    const pc = p.proposalConfidence;
    const criticalLow = pc.identity < 50 || pc.safety < 50;
    if (criticalLow) {
      return { level: "caution", label: "Proceed with Caution", detail: `${pc.identity < 50 ? "Identity" : "Safety"} score critically low (${Math.min(pc.identity, pc.safety)}%)` };
    }
    if (pc.overall >= 75 && pc.safety >= 70 && pc.identity >= 70 && pc.timing >= 60) {
      return { level: "safe", label: "Likely Safe", detail: `Overall ${pc.overall}% — identity-preserving, safe, well-timed` };
    }
    if (pc.overall >= 50 && pc.safety >= 50) {
      return { level: "review", label: "Review Recommended", detail: `Overall ${pc.overall}% — some dimensions need attention` };
    }
    return { level: "caution", label: "Proceed with Caution", detail: `Overall ${pc.overall}% — low confidence in critical dimensions` };
  }
  const passCount =
    (p.alignment >= 85 ? 1 : 0) +
    (p.confidence >= 80 ? 1 : 0) +
    (p.impact === "low" ? 1 : 0) +
    (!p.touchesInvariants ? 1 : 0) +
    (p.reversible ? 1 : 0);

  if (passCount >= 4 && !p.touchesInvariants && p.reversible) {
    return { level: "safe", label: "Low Risk", detail: `${passCount}/5 axes pass — safe to approve` };
  }
  if (p.touchesInvariants || !p.reversible || p.impact === "high") {
    return { level: "caution", label: "Review Carefully", detail: `${passCount}/5 axes pass — ${p.touchesInvariants ? "touches invariants" : !p.reversible ? "irreversible" : "high impact"}` };
  }
  return { level: "review", label: "Moderate Risk", detail: `${passCount}/5 axes pass — some concerns` };
}

/* ── Parameter Change Row ───────────────────────────────────────── */

function ParameterChangeRow({ change }: { change: ProposalParameterChange }) {
  return (
    <div className="evo-param-change">
      <div className="evo-param-change__name">{change.displayName}</div>
      <div className="evo-param-change__values">
        <span className="evo-param-change__current">{formatPayloadValue(change.currentValue)}</span>
        <span className="evo-param-change__arrow">→</span>
        <span className="evo-param-change__proposed">{formatPayloadValue(change.proposedValue)}</span>
      </div>
      {change.unit && <div className="evo-param-change__unit">{change.unit}</div>}
    </div>
  );
}

/* ── Daedalus Proposal Card ─────────────────────────────────────── */

function DaedalusProposalCard({
  proposal,
  onApprove,
  onDeny,
}: {
  proposal: DaedalusProposal;
  onApprove: (id: string) => void;
  onDeny: (id: string) => void;
}) {
  const age = Math.round((Date.now() - proposal.createdAt) / 1000);
  const ageStr = age < 60 ? `${age}s ago` : `${Math.round(age / 60)}m ago`;
  const rec = computeRecommendation(proposal);
  const paramChanges = proposal.parameterChanges ?? [];
  const boundaries = proposal.boundaries ?? [];
  const operatorImpact = proposal.operatorImpact ?? "";
  const payloadEntries = Object.entries(proposal.payload ?? {});

  return (
    <div className={`evo-daedalus-card ${rec.level === "caution" ? "evo-daedalus-card--caution" : ""}`}>
      {/* Recommendation banner */}
      <div className={`evo-rec evo-rec--${rec.level}`}>
        <span className="evo-rec__label">{rec.label}</span>
        <span className="evo-rec__detail">{rec.detail}</span>
      </div>

      <div className="evo-daedalus-card__header">
        <div className="evo-daedalus-card__left">
          <span className="evo-daedalus-card__icon">◈</span>
          <span className="evo-daedalus-card__title">{proposal.title}</span>
          <KindBadge kind={proposal.kind} />
        </div>
        <div className="evo-daedalus-card__right">
          <ImpactBadge impact={proposal.impact} />
          <span className="evo-daedalus-card__age">{ageStr}</span>
        </div>
      </div>

      <p className="evo-daedalus-card__desc">{proposal.description}</p>
      <p className="evo-daedalus-card__rationale">{proposal.rationale}</p>

      {/* Exact parameter changes with before/after */}
      {paramChanges.length > 0 && (
        <div className="evo-changes-section">
          <div className="evo-changes-section__header">
            <span className="evo-changes-section__icon">⚙</span>
            <span className="evo-changes-section__title">Exact Changes (Current → Proposed)</span>
          </div>
          <div className="evo-changes-section__list">
            {paramChanges.map(c => <ParameterChangeRow key={c.parameter} change={c} />)}
          </div>
        </div>
      )}

      {paramChanges.length === 0 && payloadEntries.length > 0 && (
        <div className="evo-payload">
          <span className="evo-payload__title">Proposed changes</span>
          <div className="evo-payload__list">
            {payloadEntries.map(([key, val]) => (
              <div className="evo-payload__item" key={key}>
                <span className="evo-payload__key">{formatPayloadKey(key)}</span>
                <span className="evo-payload__arrow">→</span>
                <span className="evo-payload__val">{formatPayloadValue(val)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* What this means for you */}
      {operatorImpact && (
        <div className="evo-operator-impact">
          <div className="evo-operator-impact__header">
            <span className="evo-operator-impact__icon">👤</span>
            <span className="evo-operator-impact__title">What This Changes For You</span>
          </div>
          <p className="evo-operator-impact__text">{operatorImpact}</p>
        </div>
      )}

      {/* What this does NOT change */}
      {boundaries.length > 0 && (
        <div className="evo-boundaries">
          <div className="evo-boundaries__header">
            <span className="evo-boundaries__icon">🔒</span>
            <span className="evo-boundaries__title">What This Does NOT Change</span>
          </div>
          <ul className="evo-boundaries__list">
            {boundaries.map((b, i) => <li key={i} className="evo-boundaries__item">{b}</li>)}
          </ul>
        </div>
      )}

      {/* Multi-dimensional confidence breakdown */}
      {proposal.proposalConfidence ? (
        <div className="evo-daedalus-card__confidence">
          <div className="evo-confidence-grid">
            <ConfidenceDimension label="Identity" value={proposal.proposalConfidence.identity} description="Will Daedalus still be Daedalus?" />
            <ConfidenceDimension label="Continuity" value={proposal.proposalConfidence.continuity} description="Will behavior remain smooth?" />
            <ConfidenceDimension label="Need" value={proposal.proposalConfidence.need} description="How necessary is this right now?" />
            <ConfidenceDimension label="Efficacy" value={proposal.proposalConfidence.efficacy} description="Will it work as intended?" />
            <ConfidenceDimension label="Safety" value={proposal.proposalConfidence.safety} description="Risk of errors or drift" />
            <ConfidenceDimension label="Timing" value={proposal.proposalConfidence.timing} description="Is now a good time?" />
            <ConfidenceDimension label="Reversibility" value={proposal.proposalConfidence.reversibility} description="How easily undone?" />
            <ConfidenceDimension label="Track Record" value={proposal.proposalConfidence.trackRecord} description="Past success for this type" />
          </div>
          <div className="evo-confidence-overall">
            <span className="evo-confidence-overall__label">Overall</span>
            <span className={`evo-confidence-overall__value evo-confidence-overall__value--${proposal.proposalConfidence.overall >= 75 ? "high" : proposal.proposalConfidence.overall >= 50 ? "mid" : "low"}`}>
              {proposal.proposalConfidence.overall}%
            </span>
            <span className="evo-confidence-overall__scope">
              Scope: {proposal.proposalConfidence.scope}
            </span>
          </div>
          {proposal.proposalConfidence.reasoning.length > 0 && (
            <div className="evo-confidence-reasoning">
              {proposal.proposalConfidence.reasoning.map((r, i) => (
                <span key={i} className="evo-confidence-reasoning__item">{r}</span>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="evo-daedalus-card__grid">
          <div className="evo-daedalus-card__metrics">
            <AlignmentBar value={proposal.alignment} label="Alignment" />
            <AlignmentBar value={proposal.confidence} label="Confidence" />
          </div>
        </div>
      )}

      {proposal.effectBaseline != null && (
        <div className="evo-baseline">
          <span className="evo-baseline__label">Baseline when proposed:</span>
          <span className="evo-baseline__val">{proposal.effectBaseline}%</span>
        </div>
      )}

      {/* Quick safety axes */}
      <div className="evo-daedalus-card__axes">
        <span className={`evo-axis ${proposal.touchesInvariants ? "evo-axis--warn" : "evo-axis--ok"}`}>
          {proposal.touchesInvariants ? "⚠ Touches Invariants" : "✓ Invariants Safe"}
        </span>
        <span className={`evo-axis ${proposal.reversible ? "evo-axis--ok" : "evo-axis--warn"}`}>
          {proposal.reversible ? "✓ Reversible" : "⚠ Irreversible"}
        </span>
        <span className={`evo-axis ${proposal.impact === "low" ? "evo-axis--ok" : proposal.impact === "medium" ? "evo-axis--neutral" : "evo-axis--warn"}`}>
          {proposal.impact === "low" ? "✓" : proposal.impact === "medium" ? "~" : "⚠"} Impact: {proposal.impact}
        </span>
        {proposal.autoApprovable && (
          <span className="evo-axis evo-axis--auto">Auto-approvable</span>
        )}
      </div>

      <div className="evo-daedalus-card__actions">
        <button className="evo-btn evo-btn--approve" onClick={() => onApprove(proposal.id)}>
          {proposal.advisory ? "Acknowledge" : "Approve"}
        </button>
        <button className="evo-btn evo-btn--deny" onClick={() => onDeny(proposal.id)}>
          {proposal.advisory ? "Dismiss" : "Deny"}
        </button>
      </div>
    </div>
  );
}

/* ── Approval Window Timer ──────────────────────────────────────── */

function ApprovalWindowTimer({ endsAt }: { endsAt: number | null }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!endsAt) return null;
  const remaining = Math.max(0, endsAt - now);
  const hours = Math.floor(remaining / 3_600_000);
  const minutes = Math.floor((remaining % 3_600_000) / 60_000);
  const seconds = Math.floor((remaining % 60_000) / 1_000);
  if (remaining === 0) return <span className="evo-timer evo-timer--expired">Window expired</span>;
  return (
    <span className="evo-timer">
      {hours > 0 ? `${hours}h ` : ""}{minutes}m {seconds}s remaining
    </span>
  );
}

/* ── Deferred Queue Summary ───────────────────────────────────── */

function DeferredQueueSummary({ queue }: { queue: ProposalQueueState }) {
  if (queue.deferredCount === 0) return null;
  return (
    <div className="evo-deferred-summary">
      <span className="evo-deferred-summary__icon">◈</span>
      <span className="evo-deferred-summary__text">
        {queue.deferredCount} proposal{queue.deferredCount !== 1 ? "s" : ""} queued
      </span>
      <div className="evo-deferred-summary__list">
        {queue.deferred.slice(0, 5).map(d => (
          <span key={d.id} className="evo-deferred-summary__item" title={d.title}>
            {d.kind} ({d.priorityScore})
          </span>
        ))}
        {queue.deferredCount > 5 && (
          <span className="evo-deferred-summary__more">+{queue.deferredCount - 5} more</span>
        )}
      </div>
    </div>
  );
}

/* ── Operator Pending Proposal Card ────────────────────────────── */

function OperatorPendingCard({
  proposal,
  onForceApprove,
  onWithdraw,
}: {
  proposal: OperatorPendingProposal;
  onForceApprove: (id: string) => void;
  onWithdraw: (id: string) => void;
}) {
  const time = new Date(proposal.createdAt).toLocaleTimeString();
  const failedAxes = Object.entries(proposal.decision.reasons)
    .filter(([, v]) => !v)
    .map(([k]) => k);

  return (
    <div className="evo-operator-pending-card">
      <div className="evo-operator-pending-card__header">
        <span className="evo-operator-pending-card__kind">{proposal.kind}</span>
        <span className="evo-operator-pending-card__time">{time}</span>
      </div>
      <p className="evo-operator-pending-card__desc">{proposal.description}</p>
      <div className="evo-operator-pending-card__reasons">
        <span className="evo-operator-pending-card__label">Failed gates:</span>
        {failedAxes.map(ax => (
          <span key={ax} className="evo-operator-pending-card__fail">{ax}</span>
        ))}
      </div>
      <div className="evo-operator-pending-card__actions">
        <button className="evo-btn evo-btn--approve" onClick={() => onForceApprove(proposal.id)}>
          Force Approve
        </button>
        <button className="evo-btn evo-btn--deny" onClick={() => onWithdraw(proposal.id)}>
          Withdraw
        </button>
      </div>
    </div>
  );
}

/* ── Operator Proposal Result Card ──────────────────────────────── */

function OperatorDecisionCard({ decision }: { decision: ApprovalDecision }) {
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
        <ImpactBadge impact={decision.derivedImpact} />
        <span className="evolution-decision__score">A:{decision.alignment}% C:{decision.confidence}%</span>
      </div>
      <div className="evolution-decision__reasons">
        {(Object.entries(decision.reasons) as [keyof ApprovalReasonBreakdown, boolean][]).map(([key, ok]) => (
          <AxesBadge key={key} label={REASON_LABELS[key]} ok={ok} />
        ))}
      </div>
    </div>
  );
}

/* ── History Card with Effect Visual ────────────────────────────── */

function HistoryRow({ entry }: { entry: ProposalHistoryEntry }) {
  const time = new Date(entry.resolvedAt).toLocaleTimeString();
  const statusClass =
    entry.status === "approved" || entry.status === "auto_approved"
      ? "evo-hist--approved"
      : entry.status === "denied"
        ? "evo-hist--denied"
        : "evo-hist--expired";

  const statusLabel = entry.status === "auto_approved" ? "auto" : entry.status;

  const deltaColor =
    entry.effectDelta == null
      ? "#6c7299"
      : entry.effectDelta > 0
        ? "#3fb950"
        : entry.effectDelta < 0
          ? "#f85149"
          : "#8b949e";

  return (
    <div className={`evo-hist-row ${statusClass}`}>
      <div className="evo-hist-row__top">
        <div className="evo-hist-row__title-row">
          <span className="evo-hist-row__title">{entry.title}</span>
          <KindBadge kind={entry.kind} />
        </div>
        <span className="evo-hist-row__status">{statusLabel}</span>
      </div>
      <div className="evo-hist-row__meta">
        <ImpactBadge impact={entry.impact} />
        <span className="evo-hist-row__time">{time}</span>
        <span className="evo-hist-row__score">A:{entry.alignment}%</span>
        <span className="evo-hist-row__score">C:{entry.confidence}%</span>
      </div>
      {(entry.effectBaseline != null || entry.effectAfter != null) && (
        <div className="evo-hist-row__baseline">
          {entry.effectBaseline != null && <span>Before: {entry.effectBaseline}%</span>}
          {entry.effectAfter != null && <span>After: {entry.effectAfter}%</span>}
        </div>
      )}
      {entry.effectDelta != null && (
        <div className="evo-hist-row__effect">
          <span className="evo-hist-row__effect-label">Effect</span>
          <div className="evo-hist-row__effect-bar-bg">
            <div
              className="evo-hist-row__effect-bar"
              style={{
                width: `${Math.min(100, Math.abs(entry.effectDelta) * 2)}%`,
                background: deltaColor,
                marginLeft: entry.effectDelta < 0 ? "auto" : undefined,
              }}
            />
          </div>
          <span className="evo-hist-row__effect-val" style={{ color: deltaColor }}>
            {entry.effectDelta > 0 ? "+" : ""}{entry.effectDelta.toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  );
}

/* ── Main Panel ─────────────────────────────────────────────────── */

export function EvolutionPanel() {
  const [queue, setQueue] = useState<ProposalQueueState | null>(null);
  const [history, setHistory] = useState<ProposalHistoryEntry[]>([]);
  const [gate, setGate] = useState<ApprovalGateResponse | null>(null);
  const [rollback, setRollback] = useState<RollbackRegistrySnapshot | null>(null);
  const [operatorPending, setOperatorPending] = useState<OperatorPendingProposal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [kind, setKind] = useState<ChangeProposalKind>("alignment_config");
  const [description, setDescription] = useState("");
  const [submitResult, setSubmitResult] = useState<ApprovalDecision | null>(null);

  const load = useCallback(async () => {
    try {
      const [q, h, g, r, op] = await Promise.all([
        fetchProposalQueue(),
        fetchProposalHistory(),
        fetchApprovalGate(),
        fetchRollbackRegistry(),
        fetchOperatorProposals(),
      ]);
      setQueue(q);
      setHistory(h);
      setGate(g);
      setRollback(r);
      setOperatorPending(op);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load evolution data");
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 6_000);
    return () => clearInterval(id);
  }, [load]);

  const handleApprove = useCallback(async (id: string) => {
    try {
      await approveDaedalusProposal(id);
      void load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
    }
  }, [load]);

  const handleDeny = useCallback(async (id: string) => {
    try {
      await denyDaedalusProposal(id);
      void load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Denial failed");
    }
  }, [load]);

  const handleForceApprove = useCallback(async (id: string) => {
    try {
      await forceApproveOperatorProposal(id);
      void load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Force approval failed");
    }
  }, [load]);

  const handleWithdraw = useCallback(async (id: string) => {
    try {
      await withdrawOperatorProposal(id);
      void load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Withdrawal failed");
    }
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

  return (
    <section className="evolution-panel">
      <div className="evolution-panel__header">
        <h3 className="evolution-panel__title">
          <span className="evolution-panel__icon">◈</span>
          Evolution
        </h3>
        {queue?.surfaced && (
          <span className="evolution-panel__badge evolution-panel__badge--pending">
            1 awaiting your {queue.surfaced.advisory ? "acknowledgment" : "approval"}
          </span>
        )}
        {(queue?.deferredCount ?? 0) > 0 && (
          <span className="evolution-panel__badge evolution-panel__badge--deferred">
            {queue!.deferredCount} queued
          </span>
        )}
      </div>

      {error && <div className="evolution-error">{error}</div>}

      {/* ── Section 1: Daedalus Proposals (single-surfaced) ──────── */}
      <div className="evo-section">
        <div className="evo-section__header">
          <span className="evo-section__title">Daedalus Proposals</span>
          <span className="evo-section__subtitle">
            One proposal at a time. Approve or deny to see the next.
          </span>
          {queue?.approvalWindowEndsAt && (
            <ApprovalWindowTimer endsAt={queue.approvalWindowEndsAt} />
          )}
        </div>

        {!queue?.surfaced ? (
          <div className="evo-section__empty">
            No active proposals. Daedalus proposes alignment corrections, self-improvements, capability expansions, resilience upgrades, and more as conditions evolve.
          </div>
        ) : (
          <div className="evo-daedalus-list">
            <DaedalusProposalCard
              proposal={queue.surfaced}
              onApprove={handleApprove}
              onDeny={handleDeny}
            />
          </div>
        )}

        {queue && <DeferredQueueSummary queue={queue} />}
      </div>

      {/* ── Section 1b: Operator Pending Proposals ─────────────────── */}
      {operatorPending.length > 0 && (
        <div className="evo-section">
          <div className="evo-section__header">
            <span className="evo-section__title">Your Pending Changes</span>
            <span className="evo-section__subtitle">
              Changes you submitted that need review. Force-approve to override.
            </span>
          </div>
          <div className="evo-operator-pending-list">
            {operatorPending.map(p => (
              <OperatorPendingCard
                key={p.id}
                proposal={p}
                onForceApprove={handleForceApprove}
                onWithdraw={handleWithdraw}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Section 2: Operator Proposals ─────────────────────────── */}
      <div className="evo-section">
        <div className="evo-section__header">
          <span className="evo-section__title">Suggest a Change</span>
          <span className="evo-section__subtitle">
            Submit proposals to be evaluated by the auto-approval gate
          </span>
        </div>

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

        {submitResult && <OperatorDecisionCard decision={submitResult} />}
      </div>

      {/* ── Section 3: History & Effect Tracker ──────────────────── */}
      <div className="evo-section">
        <div className="evo-section__header">
          <span className="evo-section__title">Proposal History</span>
          <span className="evo-section__subtitle">
            Track past proposals and their effect on alignment
          </span>
        </div>

        {rollback && (
          <div className="evolution-rollback">
            <div className="evolution-rollback__stats">
              <span className="evolution-rollback__stat">
                Active changes: <span className="evolution-rollback__num">{rollback.activeChanges.length}</span>
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

        {history.length > 0 ? (
          <div className="evo-history-list">
            {history.slice().reverse().slice(0, 20).map(entry => (
              <HistoryRow key={entry.id} entry={entry} />
            ))}
          </div>
        ) : (
          <div className="evo-section__empty">
            No proposal history yet. History will appear as proposals are approved, denied, or expire.
          </div>
        )}

        {gate && gate.recentDecisions.length > 0 && (
          <>
            <div className="evo-section__header" style={{ marginTop: 12 }}>
              <span className="evo-section__title">Gate Decisions</span>
            </div>
            <div className="evolution-decisions">
              {gate.recentDecisions.slice().reverse().slice(0, 8).map((d, i) => (
                <OperatorDecisionCard key={d.proposal.id ?? `d-${i}`} decision={d} />
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
