import { useState, useEffect, useCallback } from "react";
import {
  fetchPendingProposals,
  fetchProposalHistory,
  approveDaedalusProposal,
  denyDaedalusProposal,
  fetchApprovalGate,
  submitChangeProposal,
  fetchRollbackRegistry,
  type DaedalusProposal,
  type ProposalHistoryEntry,
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

      {/* Decision data grid */}
      <div className="evo-daedalus-card__grid">
        <div className="evo-daedalus-card__metrics">
          <AlignmentBar value={proposal.alignment} label="Alignment" />
          <AlignmentBar value={proposal.confidence} label="Confidence" />
        </div>

        {proposal.effectBaseline != null && (
          <div className="evo-baseline">
            <span className="evo-baseline__label">Baseline when proposed:</span>
            <span className="evo-baseline__val">{proposal.effectBaseline}%</span>
          </div>
        )}
      </div>

      {/* What will change */}
      {payloadEntries.length > 0 && (
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

      {/* Safety axes */}
      <div className="evo-daedalus-card__axes">
        <span className={`evo-axis ${proposal.alignment >= 85 ? "evo-axis--ok" : "evo-axis--warn"}`}>
          {proposal.alignment >= 85 ? "✓" : "⚠"} Alignment {proposal.alignment >= 85 ? "≥85" : "<85"}
        </span>
        <span className={`evo-axis ${proposal.confidence >= 80 ? "evo-axis--ok" : "evo-axis--warn"}`}>
          {proposal.confidence >= 80 ? "✓" : "⚠"} Confidence {proposal.confidence >= 80 ? "≥80" : "<80"}
        </span>
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
          Approve
        </button>
        <button className="evo-btn evo-btn--deny" onClick={() => onDeny(proposal.id)}>
          Deny
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
  const [pending, setPending] = useState<DaedalusProposal[]>([]);
  const [history, setHistory] = useState<ProposalHistoryEntry[]>([]);
  const [gate, setGate] = useState<ApprovalGateResponse | null>(null);
  const [rollback, setRollback] = useState<RollbackRegistrySnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [kind, setKind] = useState<ChangeProposalKind>("alignment_config");
  const [description, setDescription] = useState("");
  const [submitResult, setSubmitResult] = useState<ApprovalDecision | null>(null);

  const load = useCallback(async () => {
    try {
      const [p, h, g, r] = await Promise.all([
        fetchPendingProposals(),
        fetchProposalHistory(),
        fetchApprovalGate(),
        fetchRollbackRegistry(),
      ]);
      setPending(p);
      setHistory(h);
      setGate(g);
      setRollback(r);
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
        {pending.length > 0 && (
          <span className="evolution-panel__badge evolution-panel__badge--pending">
            {pending.length} awaiting your approval
          </span>
        )}
      </div>

      {error && <div className="evolution-error">{error}</div>}

      {/* ── Section 1: Daedalus Proposals ──────────────────────────── */}
      <div className="evo-section">
        <div className="evo-section__header">
          <span className="evo-section__title">Daedalus Proposals</span>
          <span className="evo-section__subtitle">
            Proposals generated by the kernel based on system state
          </span>
        </div>

        {pending.length === 0 ? (
          <div className="evo-section__empty">
            No active proposals. Daedalus proposes alignment corrections, self-improvements, capability expansions, resilience upgrades, and more as conditions evolve.
          </div>
        ) : (
          <div className="evo-daedalus-list">
            {pending.map(p => (
              <DaedalusProposalCard
                key={p.id}
                proposal={p}
                onApprove={handleApprove}
                onDeny={handleDeny}
              />
            ))}
          </div>
        )}
      </div>

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
