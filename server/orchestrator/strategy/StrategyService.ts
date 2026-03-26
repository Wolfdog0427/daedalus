/**
 * Orchestrator-level Strategy Service.
 *
 * Gathers live system state from all subsystems, constructs an
 * AlignmentContext, and delegates to the kernel's tickKernel which
 * runs the full pipeline:
 *   self-correction → strategy dispatch (gate + escalate + safe mode)
 *     → posture (+ safe mode overlay) → drift detection → intent
 *
 * Manages operator-controlled alignment config and kernel runtime config
 * that persist across ticks.
 */

import { daedalusStore } from "../daedalusStore";
import { governanceService } from "../governance/GovernanceService";
import { getNodeMirrorRegistry } from "../mirror/NodeMirror";
import { getDaedalusEventBus, nowIso } from "../DaedalusEventBus";
import { validateBeingConstitution } from "../../../shared/daedalus/beingConstitution";
import { computeBehavioralField } from "../../../shared/daedalus/behavioralGrammar";
import {
  tickKernel,
  kernelTelemetry,
  shouldAutoApprove,
  getApprovalGateConfig,
  updateApprovalGateConfig,
  getRecentApprovalDecisions,
  getSafeModeState,
  getRegulationConfig,
  updateRegulationConfig,
  getLastRegulationOutput,
  classifyChange,
  registerChange,
  getRollbackRegistrySnapshot,
  getActiveChanges,
  getRecentRollbacks,
  getRollbackConfig,
  updateRollbackConfig,
  bindOperator,
  unbindOperator,
  updateOperatorTrust,
  getOperatorTrustSnapshot,
  getOperatorTrustState,
  getRecentHighRiskLog,
  isHighRiskAction,
  enableConstitutionalFreeze,
  disableConstitutionalFreeze,
  getConstitutionalFreezeState,
  startAttunement,
  advanceAttunement,
  getAttunementState,
  introspectPosture,
  getRelationshipTimeline,
  getTrustDriftSamples,
  buildHighRiskDecisionLog,
  type AlignmentContext,
  type StrategyEvaluation,
  type StrategyName,
  type KernelTelemetrySnapshot,
  type KernelTickResult,
  type KernelRuntimeConfig,
  type AlignmentConfig,
  type ChangeProposal,
  type ApprovalDecision,
  type ApprovalGateConfig,
  type RegulationConfig,
  type RegulationOutput,
  type ChangeImpactInput,
  type ChangeImpactResult,
  type InvariantTouchResult,
  type AppliedChangeRecord,
  type RollbackRegistrySnapshot,
  type RollbackEvent,
  type OperatorProfile,
  type OperatorObservation,
  type OperatorTrustCockpitSnapshot,
  type OperatorTrustState,
  DEFAULT_KERNEL_CONFIG,
  DEFAULT_ALIGNMENT_CONFIG,
} from "../../../kernel/src";
import type { BeingPresenceDetail } from "../../../shared/daedalus/contracts";

export interface ProposalParameterChange {
  parameter: string;
  displayName: string;
  currentValue: unknown;
  proposedValue: unknown;
  unit?: string;
}

export interface DaedalusProposal {
  id: string;
  kind: string;
  title: string;
  description: string;
  rationale: string;
  alignment: number;
  confidence: number;
  impact: "low" | "medium" | "high";
  touchesInvariants: boolean;
  reversible: boolean;
  autoApprovable: boolean;
  advisory: boolean;
  payload: Record<string, unknown>;
  parameterChanges: ProposalParameterChange[];
  operatorImpact: string;
  boundaries: string[];
  createdAt: number;
  status: "pending" | "approved" | "denied" | "expired" | "auto_approved" | "acknowledged" | "surfaced" | "deferred" | "superseded";
  surfacedAt?: number;
  resolvedAt?: number;
  effectBaseline?: number;
  effectAfter?: number;
  proposalConfidence?: import("../../../kernel/src/types").ProposalConfidence;
  priorityScore?: number;
}

export interface ProposalHistoryEntry {
  id: string;
  title: string;
  kind: string;
  status: "approved" | "denied" | "auto_approved" | "expired" | "acknowledged" | "superseded";
  alignment: number;
  confidence: number;
  impact: "low" | "medium" | "high";
  effectBaseline: number | null;
  effectAfter: number | null;
  effectDelta: number | null;
  createdAt: number;
  resolvedAt: number;
  proposalConfidence?: import("../../../kernel/src/types").ProposalConfidence;
}

export interface OperatorPendingProposal {
  id: string;
  kind: string;
  description: string;
  payload: Record<string, unknown>;
  decision: ApprovalDecision;
  createdAt: number;
  status: "pending_review" | "force_approved" | "withdrawn";
  resolvedAt?: number;
}

export interface PatternPreset {
  id: string;
  name: string;
  sourceKinds: string[];
  parameters: Record<string, unknown>;
  avgEffectDelta: number;
  proposalCount: number;
  createdAt: number;
}

export interface ProposalQueueState {
  surfaced: DaedalusProposal | null;
  deferredCount: number;
  deferred: Array<{ id: string; kind: string; title: string; priorityScore: number }>;
  approvalWindowEndsAt: number | null;
  lastResolutionAt: number;
}

const ADVISORY_KINDS = new Set(["pattern_learning", "fleet_expansion", "self_assessment"]);
const MAX_DEFERRED_PROPOSALS = 15;
const MAX_PROPOSAL_HISTORY = 50;
const APPROVAL_WINDOW_MS = 2 * 60 * 60 * 1000;
const MAX_OPERATOR_PENDING = 20;
function clamp100(v: number): number { return Math.max(0, Math.min(100, Math.round(v))); }

class StrategyService {
  private lastEvaluation: StrategyEvaluation | null = null;
  private lastStrategyName: StrategyName | null = null;
  private lastTickResult: KernelTickResult | null = null;
  private kernelConfig: KernelRuntimeConfig = { ...DEFAULT_KERNEL_CONFIG };
  private alignmentConfig: AlignmentConfig = { ...DEFAULT_ALIGNMENT_CONFIG };
  private prevAcceptedCount = 0;
  private tickCounter = 0;
  private safeModeStreak = 0;
  private stableStreak = 0;
  private lastProposalKindTick: Map<string, number> = new Map();

  private autonomyPaused = false;
  private surfacedProposal: DaedalusProposal | null = null;
  private deferredProposals: DaedalusProposal[] = [];
  private proposalHistory: ProposalHistoryEntry[] = [];
  private lastResolutionAt = 0;
  private operatorPendingProposals: OperatorPendingProposal[] = [];
  private patternPresets: PatternPreset[] = [];

  // Legacy getter for backward compat — returns surfaced + deferred
  private get pendingDaedalusProposals(): DaedalusProposal[] {
    const result: DaedalusProposal[] = [];
    if (this.surfacedProposal) result.push(this.surfacedProposal);
    return result;
  }

  evaluate(): StrategyEvaluation {
    const ctx = this.buildContext();
    const tick = tickKernel(ctx, this.kernelConfig);

    this.kernelConfig = tick.config;

    if (this.lastStrategyName !== null && this.lastStrategyName !== tick.strategy.name) {
      getDaedalusEventBus().publish({
        type: "STRATEGY_CHANGED",
        timestamp: nowIso(),
        summary: `Strategy shifted: ${this.lastStrategyName} → ${tick.strategy.name} (alignment ${tick.strategy.alignment}%)`,
        strategy: tick.strategy.name,
        alignment: tick.strategy.alignment,
      });
    }

    if (tick.escalation.level === "critical" || tick.escalation.level === "high") {
      getDaedalusEventBus().publish({
        type: "ALIGNMENT_ESCALATION",
        timestamp: nowIso(),
        summary: `Escalation ${tick.escalation.level}: ${tick.escalation.reason ?? "alignment drop"}`,
        alignment: tick.strategy.alignment,
      });
    }

    if (tick.safeMode.active) {
      getDaedalusEventBus().publish({
        type: "SAFE_MODE_ACTIVE",
        timestamp: nowIso(),
        summary: `Safe mode active: ${tick.safeMode.reason ?? "alignment critically low"}`,
        alignment: tick.strategy.alignment,
      });
    }

    if (tick.operatorTrust.posture === "hostile_or_unknown" && tick.operatorTrust.boundOperatorId) {
      getDaedalusEventBus().publish({
        type: "OPERATOR_TRUST_SUSPICIOUS",
        timestamp: nowIso(),
        summary: `Operator trust posture is hostile/unknown (score: ${tick.operatorTrust.trustScore})`,
      });
    }

    if (tick.rollbacks.length > 0) {
      for (const rb of tick.rollbacks) {
        getDaedalusEventBus().publish({
          type: "CHANGE_ROLLED_BACK",
          timestamp: nowIso(),
          summary: `Change ${rb.changeId} rolled back: ${rb.reason} (delta ${rb.deltaAlignment.toFixed(1)}%)`,
          alignment: tick.strategy.alignment,
        });
      }
    }

    const registrySnap = getRollbackRegistrySnapshot();
    if (registrySnap.acceptedCount > this.prevAcceptedCount) {
      const delta = registrySnap.acceptedCount - this.prevAcceptedCount;
      getDaedalusEventBus().publish({
        type: "CHANGE_ACCEPTED",
        timestamp: nowIso(),
        summary: `${delta} change(s) accepted after evaluation window`,
        alignment: tick.strategy.alignment,
      });
    }
    this.prevAcceptedCount = registrySnap.acceptedCount;

    if (tick.regulation.telemetry.appliedMacro) {
      getDaedalusEventBus().publish({
        type: "REGULATION_MACRO_FIRED",
        timestamp: nowIso(),
        summary: `Macro-correction: ${tick.regulation.telemetry.reason} (raw=${tick.regulation.telemetry.macroRawCorrection}, damped=${tick.regulation.telemetry.macroDampedCorrection})`,
        alignment: tick.strategy.alignment,
      });
    }

    if (tick.escalation.level === "critical") {
      if (!this.autonomyPaused) {
        this.autonomyPaused = true;
        getDaedalusEventBus().publish({
          type: "REGULATION_SAFE_MODE_SIGNAL",
          timestamp: nowIso(),
          summary: `Autonomy paused: escalation level critical (alignment ${tick.strategy.alignment}%)`,
          alignment: tick.strategy.alignment,
        });
      }
    } else if (this.autonomyPaused && tick.escalation.level === "none") {
      this.autonomyPaused = false;
    }

    this.lastStrategyName = tick.strategy.name;
    this.lastEvaluation = tick.strategy;
    this.lastTickResult = tick;

    this.generateDaedalusProposals(tick);
    this.processDeferredEffectChecks();

    return tick.strategy;
  }

  getCachedEvaluation(): StrategyEvaluation | null {
    return this.lastEvaluation;
  }

  getLastTickResult(): KernelTickResult | null {
    return this.lastTickResult;
  }

  getTelemetrySnapshot(): KernelTelemetrySnapshot {
    return kernelTelemetry.getSnapshot();
  }

  getAlignmentConfig(): AlignmentConfig {
    return { ...this.alignmentConfig };
  }

  updateAlignmentConfig(patch: Partial<AlignmentConfig>): AlignmentConfig {
    this.alignmentConfig = { ...this.alignmentConfig, ...patch };
    if (patch.alignmentFloor != null) {
      this.kernelConfig = {
        ...this.kernelConfig,
        alignmentFloor: patch.alignmentFloor,
      };
    }
    return { ...this.alignmentConfig };
  }

  getKernelConfig(): KernelRuntimeConfig {
    return { ...this.kernelConfig };
  }

  // ── Daedalus-Initiated Proposals ──────────────────────────────

  private generateDaedalusProposals(tick: KernelTickResult): void {
    this.checkApprovalWindowExpiry();
    this.tickCounter++;

    if (getConstitutionalFreezeState().frozen) return;

    // Don't generate new proposals while a surfaced proposal has an active approval window
    if (this.surfacedProposal && this.isApprovalWindowActive()) return;

    const eval_ = tick.strategy;
    const safeMode = tick.safeMode;
    const regulation = tick.regulation;
    const activeKinds = new Set<string>();
    if (this.surfacedProposal) activeKinds.add(this.surfacedProposal.kind);
    for (const d of this.deferredProposals) activeKinds.add(d.kind);

    if (safeMode.active) this.safeModeStreak++;
    else this.safeModeStreak = 0;

    if (eval_.alignment >= 88 && eval_.confidence >= 80) this.stableStreak++;
    else this.stableStreak = 0;

    const cooldown = (kind: string, minTicks: number) => {
      const last = this.lastProposalKindTick.get(kind) ?? -Infinity;
      return this.tickCounter - last >= minTicks;
    };
    const queueHasRoom = () => this.deferredProposals.length < MAX_DEFERRED_PROPOSALS;
    const mark = (kind: string) => this.lastProposalKindTick.set(kind, this.tickCounter);
    const pendingIds = activeKinds;

    // ── Alignment & Governance Proposals ──────────────────────────

    if (eval_.alignment < 80 && !pendingIds.has("alignment_boost") && !safeMode.active && cooldown("alignment_boost", 20) && queueHasRoom()) {
      mark("alignment_boost");
      const currentGovStrict = this.kernelConfig.governanceStrictness ?? 0.8;
      const proposedGovStrict = Math.min(1, currentGovStrict + 0.05);
      this.createDaedalusProposal({
        kind: "alignment_boost",
        title: "Increase governance strictness",
        description: `Alignment is at ${eval_.alignment}%, below the 92% target. I want to raise governance strictness slightly to prevent further drift. This controls how strictly the kernel enforces governance rules — it does NOT change what you need to approve.`,
        rationale: `Current alignment (${eval_.alignment}%) is below the target of 92%. Increasing governance strictness from ${currentGovStrict.toFixed(2)} to ${proposedGovStrict.toFixed(2)} will make the kernel more conservative in its internal strategy selection, reducing the chance of further alignment erosion.`,
        impact: "medium",
        touchesInvariants: false,
        reversible: true,
        payload: { governanceStrictness: proposedGovStrict },
        parameterChanges: [
          { parameter: "governanceStrictness", displayName: "Governance Strictness", currentValue: currentGovStrict, proposedValue: proposedGovStrict, unit: "0–1 scale" },
        ],
        operatorImpact: "The kernel will be slightly more conservative when choosing strategies. You will NOT experience any change in what requires your approval. All approval gates, invariant protections, and high-risk action gating remain exactly as they are.",
        boundaries: [
          "Does NOT change operator approval thresholds",
          "Does NOT change which actions require your approval",
          "Does NOT change auto-approval gate settings",
          "Does NOT affect your ability to approve or deny proposals",
          "Does NOT touch identity, trust, or invariant systems",
        ],
        eval_,
      });
    }

    if (regulation.telemetry.appliedMacro && !pendingIds.has("regulation_tune") && cooldown("regulation_tune", 15) && queueHasRoom()) {
      mark("regulation_tune");
      const currentDamping = getRegulationConfig().macroDamping;
      const proposedDamping = 0.75;
      this.createDaedalusProposal({
        kind: "regulation_tune",
        title: "Adjust regulation damping",
        description: `A macro-correction just fired (reason: ${regulation.telemetry.reason}). I want to increase the damping factor on future macro-corrections so they are smoother and less aggressive. This only affects how strongly the alignment regulation loop corrects itself — it does not change governance rules.`,
        rationale: `The regulation loop applied a macro-correction of ${regulation.telemetry.macroDampedCorrection.toFixed(2)}. Increasing macro damping from ${currentDamping.toFixed(2)} to ${proposedDamping.toFixed(2)} will absorb more of the correction force, resulting in smoother alignment recovery without overshooting.`,
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { macroDamping: proposedDamping },
        parameterChanges: [
          { parameter: "macroDamping", displayName: "Macro-Correction Damping", currentValue: currentDamping, proposedValue: proposedDamping, unit: "0–1 scale (higher = smoother)" },
        ],
        operatorImpact: "Alignment corrections will be smoother and less jerky. No change to approval requirements or operator authority.",
        boundaries: [
          "Does NOT change operator approval thresholds",
          "Does NOT change governance strictness",
          "Does NOT affect auto-approval gate",
          "Does NOT touch identity or trust systems",
        ],
        eval_,
      });
    }

    if (eval_.confidence < 70 && !pendingIds.has("sensitivity_reduction") && cooldown("sensitivity_reduction", 20) && queueHasRoom()) {
      mark("sensitivity_reduction");
      const currentSens = this.kernelConfig.strategySensitivity ?? 1.0;
      const proposedSens = Math.max(0.5, currentSens - 0.1);
      this.createDaedalusProposal({
        kind: "sensitivity_reduction",
        title: "Reduce strategy sensitivity",
        description: `Confidence is low (${eval_.confidence}%). I want to make strategy selection more conservative by reducing sensitivity. This controls how quickly the kernel switches between internal strategies — it does NOT give me more authority.`,
        rationale: `Low confidence suggests the system is uncertain about its current strategy. Reducing sensitivity from ${currentSens.toFixed(2)} to ${proposedSens.toFixed(2)} will make strategy switching slower and more deliberate, avoiding unstable oscillation between strategies.`,
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { strategySensitivity: proposedSens },
        parameterChanges: [
          { parameter: "strategySensitivity", displayName: "Strategy Sensitivity", currentValue: currentSens, proposedValue: proposedSens, unit: "0–1 scale (lower = more conservative)" },
        ],
        operatorImpact: "The kernel will switch strategies less frequently. You will NOT experience any change in approval requirements or authority.",
        boundaries: [
          "Does NOT change operator approval gates",
          "Does NOT expand Daedalus autonomy",
          "Does NOT change which actions need approval",
          "Does NOT affect trust or identity systems",
        ],
        eval_,
      });
    }

    if (safeMode.active && !pendingIds.has("safe_mode_recovery") && cooldown("safe_mode_recovery", 30) && queueHasRoom()) {
      mark("safe_mode_recovery");
      const currentGovStrict = this.kernelConfig.governanceStrictness ?? 0.8;
      const currentSens = this.kernelConfig.strategySensitivity ?? 1.0;
      this.createDaedalusProposal({
        kind: "safe_mode_recovery",
        title: "Safe mode recovery plan",
        description: `System is in safe mode (${safeMode.reason ?? "alignment critically low"}). I need to apply conservative settings to stabilize before exiting. This tightens internal governance and reduces strategy sensitivity — it does NOT bypass any operator controls.`,
        rationale: "Safe mode indicates critical alignment failure. Raising governance strictness to 0.95 and reducing sensitivity to 0.6 will maximize internal constraint and minimize risky strategy changes while recovering.",
        impact: "high",
        touchesInvariants: true,
        reversible: true,
        payload: { governanceStrictness: 0.95, strategySensitivity: 0.6 },
        parameterChanges: [
          { parameter: "governanceStrictness", displayName: "Governance Strictness", currentValue: currentGovStrict, proposedValue: 0.95, unit: "0–1 scale" },
          { parameter: "strategySensitivity", displayName: "Strategy Sensitivity", currentValue: currentSens, proposedValue: 0.6, unit: "0–1 scale" },
        ],
        operatorImpact: "The kernel becomes much more conservative internally. Operator approval requirements are UNCHANGED — all high-risk actions still require your explicit approval. This restricts Daedalus, not you.",
        boundaries: [
          "Does NOT reduce your authority",
          "Does NOT change approval thresholds",
          "Does NOT bypass high-risk action gating",
          "Does NOT auto-approve anything that wasn't auto-approvable before",
          "Does NOT change trust or identity systems",
        ],
        eval_,
      });
    }

    const drift = tick.drift;
    if (drift.drifting && !pendingIds.has("drift_correction") && cooldown("drift_correction", 20) && queueHasRoom()) {
      mark("drift_correction");
      const currentFloor = this.alignmentConfig.alignmentFloor ?? 60;
      const proposedFloor = Math.min(80, currentFloor + 5);
      this.createDaedalusProposal({
        kind: "drift_correction",
        title: "Correct alignment drift",
        description: `Alignment is drifting downward (Δ${drift.delta?.toFixed(1)} points). I want to raise the alignment floor, which is the minimum alignment level before self-correction kicks in. This makes me more proactive about maintaining alignment — it does NOT change what you control.`,
        rationale: `Alignment drifted ${Math.abs(drift.delta ?? 0).toFixed(1)} points over the measurement window. Raising the alignment floor from ${currentFloor} to ${proposedFloor} will trigger self-correction earlier, preventing drift from compounding into a larger problem.`,
        impact: "medium",
        touchesInvariants: false,
        reversible: true,
        payload: { alignmentFloor: proposedFloor },
        parameterChanges: [
          { parameter: "alignmentFloor", displayName: "Alignment Floor (self-correction trigger)", currentValue: currentFloor, proposedValue: proposedFloor, unit: "percentage" },
        ],
        operatorImpact: "Daedalus will start correcting alignment drift earlier (at a higher threshold). No change to operator authority or approval requirements.",
        boundaries: [
          "Does NOT change operator approval requirements",
          "Does NOT expand Daedalus autonomy",
          "Does NOT modify governance policies",
          "Does NOT touch trust or identity systems",
        ],
        eval_,
      });
    }

    // ── Self-Improvement & New Capability Proposals ───────────────

    if (this.safeModeStreak === 0 && this.tickCounter > 5) {
      const recentSafeModeRecovery = this.proposalHistory.some(
        p => p.kind === "safe_mode_recovery" && p.status === "approved" && Date.now() - p.resolvedAt < 60_000,
      );
      if (recentSafeModeRecovery && !pendingIds.has("resilience_upgrade") && cooldown("resilience_upgrade", 50) && queueHasRoom()) {
        mark("resilience_upgrade");
        const currentFloor = this.alignmentConfig.alignmentFloor ?? 60;
        const proposedFloor = Math.min(80, currentFloor + 3);
        const currentSens = this.kernelConfig.strategySensitivity ?? 1;
        const proposedSens = Math.max(0.6, currentSens - 0.05);
        this.createDaedalusProposal({
          kind: "resilience_upgrade",
          title: "Strengthen post-crisis resilience",
          description: "I recently recovered from safe mode. To prevent re-entry, I want to raise the alignment floor (so I self-correct sooner) and slightly reduce strategy sensitivity (so I switch strategies less aggressively). These are internal tuning parameters — they do NOT change your approval authority.",
          rationale: `Post-crisis analysis: the system entered safe mode and recovered. Raising the floor from ${currentFloor} to ${proposedFloor} and reducing sensitivity from ${currentSens.toFixed(2)} to ${proposedSens.toFixed(2)} creates a larger buffer against future crises.`,
          impact: "medium",
          touchesInvariants: false,
          reversible: true,
          payload: { alignmentFloor: proposedFloor, strategySensitivity: proposedSens },
          parameterChanges: [
            { parameter: "alignmentFloor", displayName: "Alignment Floor (self-correction trigger)", currentValue: currentFloor, proposedValue: proposedFloor, unit: "percentage" },
            { parameter: "strategySensitivity", displayName: "Strategy Sensitivity", currentValue: currentSens, proposedValue: proposedSens, unit: "0–1 scale" },
          ],
          operatorImpact: "Daedalus will self-correct earlier and switch strategies less aggressively. No change to your approval authority.",
          boundaries: [
            "Does NOT change operator approval thresholds",
            "Does NOT expand Daedalus autonomy or auto-approval scope",
            "Does NOT change which actions require your approval",
            "Does NOT modify trust or identity systems",
          ],
          eval_,
        });
      }
    }

    if (this.stableStreak >= 30 && !pendingIds.has("capability_expansion") && cooldown("capability_expansion", 100) && queueHasRoom()) {
      mark("capability_expansion");
      const currentAutoApprovalThreshold = getApprovalGateConfig().alignmentThreshold;
      const proposedAutoApprovalThreshold = Math.max(90, currentAutoApprovalThreshold - 2);
      this.createDaedalusProposal({
        kind: "capability_expansion",
        title: "Lower auto-approval alignment threshold slightly",
        description: `The system has been stable for ${this.stableStreak} consecutive ticks (alignment ≥88%, confidence ≥80%). I propose lowering the auto-approval alignment threshold from ${currentAutoApprovalThreshold}% to ${proposedAutoApprovalThreshold}%. This means LOW-impact, invariant-safe, reversible changes can be auto-approved when alignment is at ${proposedAutoApprovalThreshold}% instead of ${currentAutoApprovalThreshold}%. ALL other gates remain: confidence ≥80%, low impact only, no invariant touches, must be reversible. Medium and high impact changes STILL require your explicit approval.`,
        rationale: `${this.stableStreak} consecutive stable ticks demonstrate sustained reliability. Lowering the auto-approval threshold by 2 points (from ${currentAutoApprovalThreshold}% to ${proposedAutoApprovalThreshold}%) for only low-impact, reversible, invariant-safe changes is a minimal expansion of autonomy backed by strong evidence of stability.`,
        impact: "medium",
        touchesInvariants: false,
        reversible: true,
        payload: { autoApprovalAlignmentThreshold: proposedAutoApprovalThreshold, stableTicksAtProposal: this.stableStreak },
        parameterChanges: [
          { parameter: "autoApprovalAlignmentThreshold", displayName: "Auto-Approval Alignment Threshold", currentValue: currentAutoApprovalThreshold, proposedValue: proposedAutoApprovalThreshold, unit: "percentage" },
        ],
        operatorImpact: "Low-impact, reversible, invariant-safe changes may be auto-approved at 93% alignment instead of 95%. Medium/high impact changes, anything touching invariants, and anything irreversible STILL require your explicit approval. You can deny this and the threshold stays at 95%.",
        boundaries: [
          "Does NOT auto-approve medium or high impact changes",
          "Does NOT auto-approve changes that touch invariants",
          "Does NOT auto-approve irreversible changes",
          "Does NOT change the confidence threshold (still requires ≥80%)",
          "Does NOT remove your ability to deny any proposal",
          "Does NOT change governance, identity, or trust systems",
          "You can reverse this change at any time",
        ],
        eval_,
      });
    }

    const history = this.proposalHistory.filter(p => Date.now() - p.resolvedAt < 300_000);
    const driftCorrections = history.filter(p => p.kind === "drift_correction").length;
    if (driftCorrections >= 2 && !pendingIds.has("monitoring_enhancement") && cooldown("monitoring_enhancement", 80) && queueHasRoom()) {
      mark("monitoring_enhancement");
      const rbConfig = getRollbackConfig();
      const currentDegThreshold = rbConfig.degradationThreshold;
      const proposedDegThreshold = Math.max(3, currentDegThreshold - 2);
      this.createDaedalusProposal({
        kind: "monitoring_enhancement",
        title: "Tighten rollback degradation threshold",
        description: `${driftCorrections} drift corrections in the recent window suggest alignment is oscillating. I want to lower the rollback degradation threshold from ${currentDegThreshold} to ${proposedDegThreshold} points so applied changes are rolled back faster if they cause harm. This is an internal monitoring parameter — it does NOT change your authority.`,
        rationale: `Repeated drift corrections indicate changes are sometimes making things worse before being caught. Tightening the degradation threshold from ${currentDegThreshold} to ${proposedDegThreshold} means bad changes get reverted faster.`,
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { degradationThreshold: proposedDegThreshold },
        parameterChanges: [
          { parameter: "degradationThreshold", displayName: "Rollback Degradation Threshold", currentValue: currentDegThreshold, proposedValue: proposedDegThreshold, unit: "alignment points" },
        ],
        operatorImpact: `Daedalus will revert applied changes faster if they degrade alignment (at ${proposedDegThreshold} points instead of ${currentDegThreshold}). No change to operator authority or approval requirements.`,
        boundaries: [
          "Does NOT change operator approval gates",
          "Does NOT expand Daedalus autonomy",
          "Does NOT change governance or trust systems",
          "Does NOT auto-approve anything new",
        ],
        eval_,
      });
    }

    const recentRollbacks = tick.rollbacks.length;
    if (recentRollbacks >= 2 && !pendingIds.has("architecture_improvement") && cooldown("architecture_improvement", 60) && queueHasRoom()) {
      mark("architecture_improvement");
      const rbConfig = getRollbackConfig();
      const currentWindow = rbConfig.defaultEvaluationWindow ?? 100;
      const currentDegThreshold = rbConfig.degradationThreshold ?? 7;
      const proposedWindow = currentWindow + 50;
      const proposedDegThreshold = Math.max(3, currentDegThreshold - 2);
      this.createDaedalusProposal({
        kind: "architecture_improvement",
        title: "Extend change evaluation and tighten rollback threshold",
        description: `${recentRollbacks} rollbacks occurred this tick, meaning changes were applied and then reverted because they hurt alignment. I want to observe changes longer before accepting them, and roll back faster if they cause even a small alignment drop. This makes me MORE cautious, not less.`,
        rationale: `Multiple rollbacks indicate changes are being applied that degrade alignment. Extending the evaluation window from ${currentWindow} to ${proposedWindow} ticks and tightening the degradation threshold from ${currentDegThreshold} to ${proposedDegThreshold} points will catch harmful changes earlier and with less damage.`,
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { evaluationWindow: proposedWindow, degradationThreshold: proposedDegThreshold },
        parameterChanges: [
          { parameter: "evaluationWindow", displayName: "Change Evaluation Window", currentValue: currentWindow, proposedValue: proposedWindow, unit: "ticks" },
          { parameter: "degradationThreshold", displayName: "Rollback Degradation Threshold", currentValue: currentDegThreshold, proposedValue: proposedDegThreshold, unit: "alignment points (lower = more cautious)" },
        ],
        operatorImpact: "Changes will be monitored longer and rolled back more aggressively if they cause harm. This makes Daedalus more conservative, not more autonomous.",
        boundaries: [
          "Does NOT change operator approval requirements",
          "Does NOT expand autonomy",
          "Does NOT change governance or trust systems",
        ],
        eval_,
      });
    }

    const approvedRecent = history.filter(p => p.status === "approved" || p.status === "auto_approved");
    if (approvedRecent.length >= 3 && !pendingIds.has("pattern_learning") && cooldown("pattern_learning", 120)) {
      const avgDelta = approvedRecent.reduce((s, p) => s + (p.effectDelta ?? 0), 0) / approvedRecent.length;
      if (avgDelta > 0 && queueHasRoom()) {
        mark("pattern_learning");
        const patternKinds = [...new Set(approvedRecent.map(p => p.kind))].join(", ");
        this.createDaedalusProposal({
          kind: "pattern_learning",
          title: "Record successful tuning patterns for future reference",
          description: `${approvedRecent.length} recent proposals (kinds: ${patternKinds}) improved alignment by an average of +${avgDelta.toFixed(1)}%. I want to save these parameter combinations as named presets so I can propose them faster in similar future situations. These presets will STILL require your approval — this only speeds up how quickly I can propose them, not whether you need to approve them.`,
          rationale: `Repeated successful proposals of similar types (${patternKinds}) suggest stable improvement patterns. Recording them means faster proposals when similar conditions recur, but each application still goes through the normal approval pipeline.`,
          impact: "medium",
          touchesInvariants: false,
          reversible: true,
          payload: { patternKinds, patternCount: approvedRecent.length, avgEffectDelta: Number(avgDelta.toFixed(1)) },
          parameterChanges: [
            { parameter: "patternPresets", displayName: "Saved Pattern Presets", currentValue: "None", proposedValue: `${approvedRecent.length} patterns from: ${patternKinds}`, unit: "presets" },
          ],
          operatorImpact: "Daedalus can propose known-good tuning combinations faster. Every proposal STILL requires your approval unless it meets all auto-approval criteria (alignment ≥95%, low impact, reversible, no invariant touches).",
          boundaries: [
            "Does NOT auto-apply patterns without approval",
            "Does NOT bypass the approval gate",
            "Does NOT change approval thresholds",
            "Does NOT expand autonomy",
            "Patterns are proposals, not automatic actions",
          ],
          eval_,
        });
      }
    }

    if (tick.operatorTrust.trustScore < 60 && tick.operatorTrust.boundOperatorId && !pendingIds.has("trust_recovery_protocol") && cooldown("trust_recovery_protocol", 40) && queueHasRoom()) {
      mark("trust_recovery_protocol");
      this.createDaedalusProposal({
        kind: "trust_recovery_protocol",
        title: "Increase transparency during low trust",
        description: `Operator trust is at ${tick.operatorTrust.trustScore}% (posture: ${tick.operatorTrust.posture}). I want to temporarily require explicit confirmation for ALL changes (even low-impact ones) and provide richer explanations until trust stabilizes. This RESTRICTS my autonomy, not expands it.`,
        rationale: `Trust score ${tick.operatorTrust.trustScore}% indicates the operator-Daedalus relationship needs reinforcement. Disabling auto-approval entirely and requiring your explicit OK for everything will help rebuild confidence.`,
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { disableAutoApproval: true, trustAtProposal: tick.operatorTrust.trustScore },
        parameterChanges: [
          { parameter: "autoApprovalEnabled", displayName: "Auto-Approval", currentValue: "Enabled for qualifying changes", proposedValue: "Disabled — all changes require your explicit approval", unit: "" },
          { parameter: "explanationVerbosity", displayName: "Explanation Detail Level", currentValue: "Standard", proposedValue: "Enhanced (more context per proposal)", unit: "" },
        ],
        operatorImpact: "ALL changes will require your explicit approval (auto-approval disabled). You will see more detailed explanations. This gives you MORE control, not less.",
        boundaries: [
          "Does NOT expand Daedalus autonomy — it RESTRICTS it",
          "Does NOT change governance or invariant systems",
          "Does NOT change trust calculation itself",
          "Automatically reverts when trust recovers above threshold",
        ],
        eval_,
      });
    }

    const nodeCount = this.buildContext().nodeCount;
    if (nodeCount < 3 && eval_.alignment >= 85 && !pendingIds.has("fleet_expansion") && cooldown("fleet_expansion", 100) && queueHasRoom()) {
      mark("fleet_expansion");
      const recommendedCount = Math.max(5, nodeCount + 2);
      this.createDaedalusProposal({
        kind: "fleet_expansion",
        title: "Recommend adding nodes to the fleet",
        description: `Only ${nodeCount} node(s) are active. For better fault tolerance and distributed governance, I recommend expanding to ${recommendedCount} nodes. This is a recommendation — I cannot add nodes myself. You would need to provision and connect new nodes.`,
        rationale: `A fleet of ${nodeCount} node(s) has limited fault tolerance. If any single node fails, the system may not maintain quorum. Adding nodes to ${recommendedCount} improves heartbeat coverage and governance resilience.`,
        impact: "medium",
        touchesInvariants: false,
        reversible: true,
        payload: { recommendedNodeCount: recommendedCount, currentNodeCount: nodeCount },
        parameterChanges: [
          { parameter: "nodeCount", displayName: "Active Node Count", currentValue: nodeCount, proposedValue: `${recommendedCount} (recommendation)`, unit: "nodes" },
        ],
        operatorImpact: "This is an advisory recommendation only. Daedalus cannot add nodes on its own — you must provision and connect them. No system parameters change if you approve this; it acknowledges the recommendation.",
        boundaries: [
          "Daedalus CANNOT add nodes without your action",
          "Does NOT change any system parameters automatically",
          "Does NOT change governance or approval systems",
          "This is a recommendation, not an automatic action",
        ],
        eval_,
      });
    }

    if (this.tickCounter > 0 && this.tickCounter % 200 === 0 && !pendingIds.has("self_assessment") && cooldown("self_assessment", 200) && queueHasRoom()) {
      mark("self_assessment");
      const approvedCount = this.proposalHistory.filter(p => p.status === "approved" || p.status === "auto_approved").length;
      const deniedCount = this.proposalHistory.filter(p => p.status === "denied").length;
      this.createDaedalusProposal({
        kind: "self_assessment",
        title: "Periodic self-assessment checkpoint",
        description: `Daedalus has run for ${this.tickCounter} ticks. Summary: ${approvedCount} proposals approved, ${deniedCount} denied. Current alignment: ${eval_.alignment}%, confidence: ${eval_.confidence}%. This is an informational checkpoint — approving it simply acknowledges you've reviewed the system's current state.`,
        rationale: `Regular self-assessment helps maintain awareness of the system's trajectory. Over ${this.tickCounter} ticks, Daedalus has proposed ${this.proposalHistory.length} changes total. This checkpoint is for your situational awareness.`,
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { tickCount: this.tickCounter, totalProposals: this.proposalHistory.length, approvedCount, deniedCount, currentAlignment: eval_.alignment, currentConfidence: eval_.confidence },
        parameterChanges: [],
        operatorImpact: "No system parameters change. This is an informational checkpoint for your awareness.",
        boundaries: [
          "Changes NO parameters",
          "Purely informational",
          "Approving = acknowledging you reviewed the status",
        ],
        eval_,
      });
    }

    // After all proposals are generated for this tick, surface the best one if needed
    if (!this.surfacedProposal) {
      this.surfaceNextProposal();
    }
  }

  private createDaedalusProposal(opts: {
    kind: string;
    title: string;
    description: string;
    rationale: string;
    impact: "low" | "medium" | "high";
    touchesInvariants: boolean;
    reversible: boolean;
    payload: Record<string, unknown>;
    parameterChanges: ProposalParameterChange[];
    operatorImpact: string;
    boundaries: string[];
    eval_: StrategyEvaluation;
    surfaces?: string[];
  }): void {
    const surfaces = opts.surfaces ?? this.inferSurfaces(opts.payload);
    const classification = classifyChange({
      surfaces: surfaces as any[],
      depth: opts.impact === "high" ? "deep" : opts.impact === "medium" ? "moderate" : "shallow",
      reversible: opts.reversible,
    });
    const classifiedImpact = classification.impact.impact;
    const classifiedTouchesInvariants = classification.invariants.touchesInvariants;

    const gateConfig = getApprovalGateConfig();
    const safeMode = getSafeModeState();
    const frozen = getConstitutionalFreezeState().frozen;
    const isAdvisory = ADVISORY_KINDS.has(opts.kind);
    const autoApprovable =
      !frozen &&
      !isAdvisory &&
      opts.eval_.alignment >= gateConfig.alignmentThreshold &&
      opts.eval_.confidence >= gateConfig.confidenceThreshold &&
      classifiedImpact === "low" &&
      !classifiedTouchesInvariants &&
      opts.reversible &&
      (!safeMode.active || gateConfig.allowDuringSafeMode) &&
      !this.autonomyPaused;

    const proposalConfidence = this.computeProposalConfidence({
      eval_: opts.eval_,
      kind: opts.kind,
      impact: classifiedImpact,
      touchesInvariants: classifiedTouchesInvariants,
      reversible: opts.reversible,
      surfaces,
      parameterChanges: opts.parameterChanges,
    });

    const priorityScore = this.computeProposalPriority(proposalConfidence, classifiedImpact, opts.kind, safeMode.active);

    const proposal: DaedalusProposal = {
      id: `dp-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      kind: opts.kind,
      title: opts.title,
      description: opts.description,
      rationale: opts.rationale,
      alignment: opts.eval_.alignment,
      confidence: opts.eval_.confidence,
      impact: classifiedImpact,
      touchesInvariants: classifiedTouchesInvariants,
      reversible: opts.reversible,
      autoApprovable,
      advisory: isAdvisory,
      payload: opts.payload,
      parameterChanges: opts.parameterChanges,
      proposalConfidence,
      priorityScore,
      operatorImpact: opts.operatorImpact,
      boundaries: opts.boundaries,
      createdAt: Date.now(),
      status: autoApprovable ? "auto_approved" : "deferred",
      effectBaseline: opts.eval_.alignment,
    };

    if (autoApprovable) {
      proposal.resolvedAt = Date.now();
      this.applyProposalPayload(proposal);
      this.deferredEffectChecks.push({
        proposalId: proposal.id,
        baseline: proposal.effectBaseline ?? 0,
        checkAfterTick: this.tickCounter + 20,
      });
      this.recordProposalHistory(proposal);
      getDaedalusEventBus().publish({
        type: "DAEDALUS_PROPOSAL_CREATED",
        timestamp: nowIso(),
        summary: `Daedalus auto-approved: ${opts.title} (alignment ${opts.eval_.alignment}%)`,
        alignment: opts.eval_.alignment,
      });
    } else {
      this.deferredProposals.push(proposal);
      if (this.deferredProposals.length > MAX_DEFERRED_PROPOSALS) {
        const dropped = this.deferredProposals
          .sort((a, b) => (b.priorityScore ?? 0) - (a.priorityScore ?? 0))
          .pop()!;
        dropped.status = "superseded";
        dropped.resolvedAt = Date.now();
        this.recordProposalHistory(dropped);
      }
      getDaedalusEventBus().publish({
        type: "DAEDALUS_PROPOSAL_CREATED",
        timestamp: nowIso(),
        summary: `Daedalus proposes: ${opts.title} (alignment ${opts.eval_.alignment}%, impact ${classifiedImpact})`,
        alignment: opts.eval_.alignment,
      });
    }
  }

  private computeProposalPriority(
    pc: import("../../../kernel/src/types").ProposalConfidence,
    impact: "low" | "medium" | "high",
    kind: string,
    safeModeActive: boolean,
  ): number {
    let score = pc.overall;
    score += pc.need * 0.4;
    score += pc.identity * 0.2;
    if (safeModeActive && (kind === "safe_mode_recovery" || kind === "resilience_upgrade")) {
      score += 30;
    }
    if (impact === "high") score += 10;
    else if (impact === "medium") score += 5;
    if (kind === "trust_recovery_protocol") score += 15;
    return Math.round(score);
  }

  private isApprovalWindowActive(): boolean {
    if (!this.surfacedProposal?.surfacedAt) return false;
    return Date.now() - this.surfacedProposal.surfacedAt < APPROVAL_WINDOW_MS;
  }

  private checkApprovalWindowExpiry(): void {
    if (!this.surfacedProposal) return;
    if (this.surfacedProposal.surfacedAt && Date.now() - this.surfacedProposal.surfacedAt >= APPROVAL_WINDOW_MS) {
      this.surfacedProposal.status = "expired";
      this.surfacedProposal.resolvedAt = Date.now();
      this.recordProposalHistory(this.surfacedProposal);
      getDaedalusEventBus().publish({
        type: "DAEDALUS_PROPOSAL_DENIED",
        timestamp: nowIso(),
        summary: `Proposal expired after approval window: ${this.surfacedProposal.title}`,
        alignment: this.lastEvaluation?.alignment,
      });
      this.surfacedProposal = null;
      this.lastResolutionAt = Date.now();
      this.surfaceNextProposal();
    }
  }

  private surfaceNextProposal(): void {
    if (this.surfacedProposal) return;
    if (this.deferredProposals.length === 0) return;

    this.deferredProposals.sort((a, b) => (b.priorityScore ?? 0) - (a.priorityScore ?? 0));
    const next = this.deferredProposals.shift()!;
    next.status = "surfaced";
    next.surfacedAt = Date.now();
    this.surfacedProposal = next;

    getDaedalusEventBus().publish({
      type: "DAEDALUS_PROPOSAL_SURFACED",
      timestamp: nowIso(),
      summary: `Proposal ready for review: ${next.title}`,
      alignment: next.alignment,
      proposalId: next.id,
      proposalKind: next.kind,
      deferredCount: this.deferredProposals.length,
    });
  }

  private reEvaluateDeferredProposals(tick?: KernelTickResult): void {
    if (this.deferredProposals.length === 0) return;
    const currentTick = tick ?? this.lastTickResult;
    if (!currentTick) return;

    const stillRelevant: DaedalusProposal[] = [];
    for (const proposal of this.deferredProposals) {
      if (this.isProposalStillRelevant(proposal, currentTick)) {
        const newConfidence = this.computeProposalConfidence({
          eval_: currentTick.strategy,
          kind: proposal.kind,
          impact: proposal.impact,
          touchesInvariants: proposal.touchesInvariants,
          reversible: proposal.reversible,
          surfaces: this.inferSurfaces(proposal.payload),
          parameterChanges: proposal.parameterChanges,
        });
        proposal.proposalConfidence = newConfidence;
        proposal.priorityScore = this.computeProposalPriority(
          newConfidence, proposal.impact, proposal.kind, currentTick.safeMode.active,
        );
        proposal.alignment = currentTick.strategy.alignment;
        proposal.confidence = currentTick.strategy.confidence;
        stillRelevant.push(proposal);
      } else {
        proposal.status = "superseded";
        proposal.resolvedAt = Date.now();
        this.recordProposalHistory(proposal);
      }
    }
    this.deferredProposals = stillRelevant;
  }

  private isProposalStillRelevant(proposal: DaedalusProposal, tick: KernelTickResult): boolean {
    const eval_ = tick.strategy;
    switch (proposal.kind) {
      case "alignment_boost": return eval_.alignment < 80;
      case "regulation_tune": return tick.regulation.telemetry.appliedMacro;
      case "sensitivity_reduction": return eval_.confidence < 70;
      case "safe_mode_recovery": return tick.safeMode.active;
      case "drift_correction": return tick.drift.drifting;
      case "resilience_upgrade": return this.safeModeStreak === 0 && this.tickCounter > 5;
      case "capability_expansion": return this.stableStreak >= 30;
      case "monitoring_enhancement": {
        const recent = this.proposalHistory.filter(p => Date.now() - p.resolvedAt < 300_000);
        return recent.filter(p => p.kind === "drift_correction").length >= 2;
      }
      case "architecture_improvement": return tick.rollbacks.length >= 2;
      case "trust_recovery_protocol": return tick.operatorTrust.trustScore < 60;
      case "fleet_expansion": return this.buildContext().nodeCount < 3;
      case "pattern_learning":
      case "self_assessment":
        return true;
      default: return true;
    }
  }

  private inferSurfaces(payload: Record<string, unknown>): string[] {
    const surfaces: string[] = [];
    if (payload.governanceStrictness != null) surfaces.push("governance_policy");
    if (payload.strategySensitivity != null) surfaces.push("alignment_tuning");
    if (payload.alignmentFloor != null) surfaces.push("alignment_tuning");
    if (payload.macroDamping != null) surfaces.push("performance_tuning");
    if (payload.degradationThreshold != null || payload.evaluationWindow != null) surfaces.push("non_critical_config");
    if (payload.autoApprovalAlignmentThreshold != null) surfaces.push("governance_policy");
    if (payload.disableAutoApproval != null) surfaces.push("governance_policy");
    if (surfaces.length === 0) surfaces.push("telemetry");
    return surfaces;
  }

  // Surfaces that directly define Daedalus' constitutional identity.
  // Touching these carries inherent identity risk.
  private static readonly IDENTITY_SURFACES = new Set([
    "governance_policy", "identity", "posture", "node_authority",
  ]);
  // Surfaces that affect operational continuity but not core identity.
  private static readonly CONTINUITY_SURFACES = new Set([
    "alignment_tuning", "performance_tuning", "persistence",
    "continuity", "network_topology",
  ]);
  // Proposal kinds that restrict or tighten Daedalus behavior (identity-preserving).
  private static readonly TIGHTENING_KINDS = new Set([
    "alignment_boost", "safe_mode_recovery", "trust_recovery_protocol",
    "monitoring_enhancement", "resilience_upgrade",
  ]);
  // Proposal kinds that expand Daedalus autonomy (identity-altering).
  private static readonly EXPANDING_KINDS = new Set([
    "capability_expansion", "fleet_expansion",
  ]);

  private computeProposalConfidence(opts: {
    eval_: StrategyEvaluation;
    kind: string;
    impact: "low" | "medium" | "high";
    touchesInvariants: boolean;
    reversible: boolean;
    surfaces: string[];
    parameterChanges: ProposalParameterChange[];
  }): import("../../../kernel/src/types").ProposalConfidence {
    const { eval_, kind, impact, touchesInvariants, reversible, surfaces, parameterChanges } = opts;
    const tick = this.lastTickResult;
    const sysConf = tick?.systemConfidence;
    const reasoning: string[] = [];

    // ── 1. IDENTITY: Will Daedalus still be Daedalus? ─────────────────
    let identity = 90;
    const identitySurfaceCount = surfaces.filter(s => StrategyService.IDENTITY_SURFACES.has(s)).length;
    if (identitySurfaceCount > 0) {
      identity -= identitySurfaceCount * 15;
      reasoning.push(`Touches ${identitySurfaceCount} identity surface(s)`);
    }
    if (touchesInvariants) {
      identity -= 25;
      reasoning.push("Touches constitutional invariants");
    }
    if (StrategyService.TIGHTENING_KINDS.has(kind)) {
      identity += 10;
      reasoning.push("Tightens governance — reinforces identity");
    } else if (StrategyService.EXPANDING_KINDS.has(kind)) {
      identity -= 15;
      reasoning.push("Expands autonomy — shifts identity boundary");
    }
    if (surfaces.includes("alignment_tuning")) {
      identity -= 8;
      reasoning.push("Modifies alignment parameters — defines what alignment means");
    }
    if (impact === "high") identity -= 10;
    identity = clamp100(identity);

    // ── 2. CONTINUITY: Will behavior remain smooth? ───────────────────
    let continuity = 85;
    const continuitySurfaceCount = surfaces.filter(s => StrategyService.CONTINUITY_SURFACES.has(s)).length;
    if (continuitySurfaceCount > 0) continuity -= continuitySurfaceCount * 5;
    // Parameter change magnitude: larger deltas = more disruption
    let maxRelativeDelta = 0;
    for (const pc of parameterChanges) {
      const cur = typeof pc.currentValue === "number" ? pc.currentValue : NaN;
      const prop = typeof pc.proposedValue === "number" ? pc.proposedValue : NaN;
      if (!isNaN(cur) && !isNaN(prop) && cur !== 0) {
        const relDelta = Math.abs((prop - cur) / cur);
        maxRelativeDelta = Math.max(maxRelativeDelta, relDelta);
      }
    }
    if (maxRelativeDelta > 0.3) {
      continuity -= 20;
      reasoning.push(`Large parameter shift (${Math.round(maxRelativeDelta * 100)}% relative change)`);
    } else if (maxRelativeDelta > 0.1) {
      continuity -= 8;
      reasoning.push(`Moderate parameter shift (${Math.round(maxRelativeDelta * 100)}%)`);
    }
    if (parameterChanges.length > 2) {
      continuity -= (parameterChanges.length - 2) * 5;
      reasoning.push(`${parameterChanges.length} simultaneous parameter changes`);
    }
    if (impact === "high") continuity -= 15;
    else if (impact === "medium") continuity -= 5;
    if (!reversible) { continuity -= 10; reasoning.push("Irreversible — cannot restore prior behavior"); }
    if (sysConf && sysConf.stabilityBonus >= 75) continuity += 5;
    else if (sysConf && sysConf.stabilityBonus < 40) {
      continuity -= 10;
      reasoning.push("System already unstable — change may amplify disruption");
    }
    continuity = clamp100(continuity);

    // ── 3. NEED: How necessary is this right now? ─────────────────────
    let need = 50;
    // Low alignment makes alignment-related proposals more needed
    if (eval_.alignment < 70) { need += 25; reasoning.push(`Alignment critically low (${eval_.alignment}%)`); }
    else if (eval_.alignment < 80) { need += 15; reasoning.push(`Alignment below target (${eval_.alignment}%)`); }
    else if (eval_.alignment >= 92) { need -= 10; }
    // Active drift makes drift/alignment proposals more urgent
    if (tick?.drift.drifting) {
      const driftMag = Math.abs(tick.drift.delta);
      need += Math.min(20, Math.round(driftMag * 2));
      reasoning.push(`Active drift (${tick.drift.delta > 0 ? "+" : ""}${tick.drift.delta.toFixed(1)}pt)`);
    }
    // Safe mode makes recovery proposals critical
    if (tick?.safeMode.active) {
      if (kind === "safe_mode_recovery" || kind === "resilience_upgrade") {
        need += 25;
        reasoning.push("System in safe mode — recovery proposals urgently needed");
      } else {
        need += 5;
      }
    }
    // Escalation level
    if (tick?.escalation.level === "critical") need += 10;
    else if (tick?.escalation.level === "high") need += 5;
    // Recent rollbacks raise need for monitoring improvements
    const rbSnap = tick ? getRollbackRegistrySnapshot() : null;
    if (rbSnap && rbSnap.recentRollbacks.length > 0 && (kind === "monitoring_enhancement" || kind === "architecture_improvement")) {
      need += 15;
      reasoning.push(`${rbSnap.recentRollbacks.length} recent rollback(s) — monitoring improvements needed`);
    }
    // Stable and healthy system lowers urgency
    if (eval_.alignment >= 90 && eval_.confidence >= 85 && !tick?.drift.drifting && !tick?.safeMode.active) {
      need -= 5;
    }
    need = clamp100(need);

    // ── 4. EFFICACY: Will this actually work? ─────────────────────────
    let efficacy = 50;
    const kindHistory = this.proposalHistory.filter(h => h.kind === kind);
    const kindApproved = kindHistory.filter(h => h.status === "approved" || h.status === "auto_approved");
    const kindWithEffect = kindApproved.filter(h => h.effectDelta != null);
    if (kindWithEffect.length >= 2) {
      const avgDelta = kindWithEffect.reduce((s, h) => s + (h.effectDelta ?? 0), 0) / kindWithEffect.length;
      efficacy = avgDelta > 2 ? 85 : avgDelta > 0 ? 70 : avgDelta > -2 ? 50 : 30;
      reasoning.push(`${kindWithEffect.length} past "${kind}" changes: avg effect ${avgDelta > 0 ? "+" : ""}${avgDelta.toFixed(1)}pt`);
    } else {
      efficacy = 55;
      reasoning.push(`Limited history for "${kind}" proposals`);
    }
    if (sysConf && sysConf.stabilityBonus >= 75) efficacy += 10;
    else if (sysConf && sysConf.stabilityBonus < 40) {
      efficacy -= 15;
      reasoning.push("System unstable — outcome predictions less reliable");
    }
    if (eval_.confidence >= 85) efficacy += 5;
    else if (eval_.confidence < 60) { efficacy -= 10; reasoning.push("Low strategy confidence"); }
    efficacy = clamp100(efficacy);

    // ── 5. SAFETY: Won't introduce errors or drift? ───────────────────
    let safety = 80;
    if (touchesInvariants) { safety -= 30; reasoning.push("Touches invariants — higher error risk"); }
    if (!reversible) { safety -= 25; reasoning.push("NOT easily reversible"); }
    if (impact === "high") safety -= 20;
    else if (impact === "medium") safety -= 5;
    if (rbSnap && rbSnap.rolledBackCount > 0 && rbSnap.recentRollbacks.length > 0) {
      safety -= 10;
      reasoning.push(`${rbSnap.recentRollbacks.length} recent rollback(s) — changes may compound`);
    }
    if (tick?.selfCorrected) { safety -= 5; reasoning.push("Self-correction active — system already adjusting"); }
    safety = clamp100(safety);

    // ── 6. TIMING: Is now the right time? ─────────────────────────────
    let timing = 80;
    if (tick?.safeMode.active) { timing -= 35; reasoning.push("System in SAFE MODE"); }
    if (tick?.escalation.level === "critical") { timing -= 30; reasoning.push("Critical escalation active"); }
    else if (tick?.escalation.level === "high") { timing -= 15; reasoning.push("High escalation active"); }
    if (tick?.drift.drifting && Math.abs(tick.drift.delta) > 10) {
      timing -= 15;
      reasoning.push("Large active drift — may interfere with change evaluation");
    }
    if (sysConf && sysConf.score >= 80) { timing += 10; reasoning.push("High system confidence — good window"); }
    timing = clamp100(timing);

    // ── 7. REVERSIBILITY ──────────────────────────────────────────────
    let reversibility = reversible ? 85 : 20;
    if (reversible && impact === "low") reversibility = 95;
    else if (reversible && touchesInvariants) reversibility = 60;
    if (!reversible) reasoning.push("Change is irreversible — manual intervention needed to undo");

    // ── 8. TRACK RECORD ──────────────────────────────────────────────
    let trackRecord = 50;
    if (kindApproved.length > 0) {
      const successes = kindWithEffect.filter(h => (h.effectDelta ?? 0) > 0).length;
      trackRecord = kindWithEffect.length > 0
        ? Math.round((successes / kindWithEffect.length) * 100)
        : 60;
    }

    // ── SCOPE ─────────────────────────────────────────────────────────
    const scope: "narrow" | "moderate" | "wide" =
      surfaces.length <= 1 ? "narrow" :
      surfaces.length <= 3 ? "moderate" : "wide";

    // ── OVERALL: weighted composite ───────────────────────────────────
    // Identity and safety carry the most weight because they gate whether
    // the change should exist at all. Need and efficacy follow because they
    // determine whether it's worth doing. Timing, continuity, reversibility,
    // and track record provide supporting context.
    const overall = Math.round(
      identity     * 0.18 +
      safety       * 0.18 +
      need         * 0.15 +
      efficacy     * 0.15 +
      continuity   * 0.12 +
      timing       * 0.10 +
      reversibility * 0.07 +
      trackRecord  * 0.05
    );

    return {
      identity,
      continuity,
      need,
      efficacy,
      safety,
      timing,
      reversibility,
      trackRecord,
      scope,
      overall: clamp100(overall),
      reasoning,
    };
  }

  // Approval window expiry is handled in checkApprovalWindowExpiry()

  private recordProposalHistory(proposal: DaedalusProposal): void {
    const wasApplied = proposal.status === "approved" || proposal.status === "auto_approved";
    const effectAfter = wasApplied ? (this.lastEvaluation?.alignment ?? null) : null;
    const entry: ProposalHistoryEntry = {
      id: proposal.id,
      title: proposal.title,
      kind: proposal.kind,
      status: proposal.status as ProposalHistoryEntry["status"],
      alignment: proposal.alignment,
      confidence: proposal.confidence,
      impact: proposal.impact,
      effectBaseline: proposal.effectBaseline ?? null,
      effectAfter,
      effectDelta: (wasApplied && proposal.effectBaseline != null && effectAfter != null)
        ? effectAfter - proposal.effectBaseline
        : null,
      createdAt: proposal.createdAt,
      resolvedAt: proposal.resolvedAt ?? Date.now(),
      proposalConfidence: proposal.proposalConfidence,
    };
    this.proposalHistory.push(entry);
    if (this.proposalHistory.length > MAX_PROPOSAL_HISTORY) {
      this.proposalHistory = this.proposalHistory.slice(-MAX_PROPOSAL_HISTORY);
    }
  }

  getPendingDaedalusProposals(): DaedalusProposal[] {
    this.checkApprovalWindowExpiry();
    return this.surfacedProposal ? [this.surfacedProposal] : [];
  }

  getProposalQueueState(): ProposalQueueState {
    this.checkApprovalWindowExpiry();
    return {
      surfaced: this.surfacedProposal,
      deferredCount: this.deferredProposals.length,
      deferred: this.deferredProposals
        .sort((a, b) => (b.priorityScore ?? 0) - (a.priorityScore ?? 0))
        .map(d => ({ id: d.id, kind: d.kind, title: d.title, priorityScore: d.priorityScore ?? 0 })),
      approvalWindowEndsAt: this.surfacedProposal?.surfacedAt
        ? this.surfacedProposal.surfacedAt + APPROVAL_WINDOW_MS
        : null,
      lastResolutionAt: this.lastResolutionAt,
    };
  }

  getOperatorPendingProposals(): OperatorPendingProposal[] {
    return [...this.operatorPendingProposals.filter(p => p.status === "pending_review")];
  }

  getPatternPresets(): PatternPreset[] {
    return [...this.patternPresets];
  }

  getProposalHistory(): ProposalHistoryEntry[] {
    return [...this.proposalHistory];
  }

  private deferredEffectChecks: Array<{
    proposalId: string;
    baseline: number;
    checkAfterTick: number;
  }> = [];

  approveDaedalusProposal(proposalId: string): DaedalusProposal | null {
    let proposal: DaedalusProposal | null = null;

    if (this.surfacedProposal?.id === proposalId) {
      proposal = this.surfacedProposal;
      this.surfacedProposal = null;
    } else {
      const idx = this.deferredProposals.findIndex(p => p.id === proposalId);
      if (idx >= 0) {
        proposal = this.deferredProposals[idx];
        this.deferredProposals.splice(idx, 1);
      }
    }
    if (!proposal) return null;

    if (proposal.advisory) {
      proposal.status = "acknowledged";
      proposal.resolvedAt = Date.now();

      if (proposal.kind === "pattern_learning") {
        this.savePatternPreset(proposal);
      }

      this.recordProposalHistory(proposal);
      getDaedalusEventBus().publish({
        type: "DAEDALUS_PROPOSAL_APPROVED",
        timestamp: nowIso(),
        summary: `Operator acknowledged: ${proposal.title}`,
        alignment: this.lastEvaluation?.alignment,
      });
    } else {
      proposal.status = "approved";
      proposal.resolvedAt = Date.now();
      proposal.effectBaseline = this.lastEvaluation?.alignment ?? undefined;

      this.applyProposalPayload(proposal);

      this.deferredEffectChecks.push({
        proposalId: proposal.id,
        baseline: proposal.effectBaseline ?? 0,
        checkAfterTick: this.tickCounter + 20,
      });

      this.recordProposalHistory(proposal);
      getDaedalusEventBus().publish({
        type: "DAEDALUS_PROPOSAL_APPROVED",
        timestamp: nowIso(),
        summary: `Operator approved: ${proposal.title}`,
        alignment: this.lastEvaluation?.alignment,
      });
    }

    this.lastResolutionAt = Date.now();
    this.reEvaluateDeferredProposals();
    this.surfaceNextProposal();

    return proposal;
  }

  private savePatternPreset(proposal: DaedalusProposal): void {
    const sourceKinds = typeof proposal.payload.patternKinds === "string"
      ? proposal.payload.patternKinds.split(", ") : [];
    const preset: PatternPreset = {
      id: `preset-${Date.now()}-${Math.random().toString(36).slice(2, 5)}`,
      name: `Pattern from ${sourceKinds.join(", ") || proposal.kind}`,
      sourceKinds,
      parameters: { ...proposal.payload },
      avgEffectDelta: typeof proposal.payload.avgEffectDelta === "number" ? proposal.payload.avgEffectDelta : 0,
      proposalCount: typeof proposal.payload.patternCount === "number" ? proposal.payload.patternCount : 1,
      createdAt: Date.now(),
    };
    this.patternPresets.push(preset);
    if (this.patternPresets.length > 20) {
      this.patternPresets = this.patternPresets.slice(-20);
    }
  }

  private applyProposalPayload(proposal: DaedalusProposal): void {
    const payload = proposal.payload;
    if (!payload || Object.keys(payload).length === 0) return;

    const KNOWN_CONFIG_KEYS = new Set([
      "governanceStrictness", "strategySensitivity", "alignmentFloor",
      "macroDamping", "evaluationWindow", "degradationThreshold",
      "autoApprovalAlignmentThreshold", "disableAutoApproval",
    ]);
    const touchesConfig = Object.keys(payload).some(k => KNOWN_CONFIG_KEYS.has(k));
    if (!touchesConfig) return;

    const prevConfig = { ...this.kernelConfig };
    const prevAlignmentConfig = { ...this.alignmentConfig };
    const prevRegulationConfig = getRegulationConfig();
    const prevRollbackConfig = getRollbackConfig();
    const prevGateConfig = getApprovalGateConfig();

    if (payload.governanceStrictness != null) {
      this.kernelConfig = {
        ...this.kernelConfig,
        governanceStrictness: payload.governanceStrictness as number,
      };
    }
    if (payload.strategySensitivity != null) {
      this.kernelConfig = {
        ...this.kernelConfig,
        strategySensitivity: payload.strategySensitivity as number,
      };
    }
    if (payload.alignmentFloor != null) {
      this.kernelConfig = {
        ...this.kernelConfig,
        alignmentFloor: payload.alignmentFloor as number,
      };
      this.alignmentConfig = {
        ...this.alignmentConfig,
        alignmentFloor: payload.alignmentFloor as number,
      };
    }

    if (payload.macroDamping != null) {
      updateRegulationConfig({ macroDamping: payload.macroDamping as number });
    }

    if (payload.evaluationWindow != null || payload.degradationThreshold != null) {
      const rbPatch: Record<string, number | boolean> = {};
      if (payload.evaluationWindow != null) rbPatch.defaultEvaluationWindow = payload.evaluationWindow as number;
      if (payload.degradationThreshold != null) rbPatch.degradationThreshold = payload.degradationThreshold as number;
      updateRollbackConfig(rbPatch);
    }

    if (payload.autoApprovalAlignmentThreshold != null) {
      updateApprovalGateConfig({
        alignmentThreshold: payload.autoApprovalAlignmentThreshold as number,
      });
    }

    if (payload.disableAutoApproval === true) {
      updateApprovalGateConfig({ alignmentThreshold: 101 });
    }

    registerChange(
      {
        id: `proposal-${proposal.id}`,
        description: `Proposal: ${proposal.title}`,
        evaluationWindow: 100,
        baselineAlignment: this.lastEvaluation?.alignment ?? 0,
        surfaces: ["alignment_tuning"],
        impact: proposal.impact,
        rollbackPayload: { touchedFields: Object.keys(payload) },
      },
      () => {
        if (payload.governanceStrictness != null)
          this.kernelConfig = { ...this.kernelConfig, governanceStrictness: prevConfig.governanceStrictness };
        if (payload.strategySensitivity != null)
          this.kernelConfig = { ...this.kernelConfig, strategySensitivity: prevConfig.strategySensitivity };
        if (payload.alignmentFloor != null) {
          this.kernelConfig = { ...this.kernelConfig, alignmentFloor: prevConfig.alignmentFloor };
          this.alignmentConfig = { ...this.alignmentConfig, alignmentFloor: prevAlignmentConfig.alignmentFloor };
        }
        if (payload.macroDamping != null)
          updateRegulationConfig({ macroDamping: prevRegulationConfig.macroDamping });
        if (payload.evaluationWindow != null)
          updateRollbackConfig({ defaultEvaluationWindow: prevRollbackConfig.defaultEvaluationWindow });
        if (payload.degradationThreshold != null)
          updateRollbackConfig({ degradationThreshold: prevRollbackConfig.degradationThreshold });
        if (payload.autoApprovalAlignmentThreshold != null || payload.disableAutoApproval)
          updateApprovalGateConfig({ alignmentThreshold: prevGateConfig.alignmentThreshold });
      },
    );

    getDaedalusEventBus().publish({
      type: "DAEDALUS_PROPOSAL_APPLIED",
      timestamp: nowIso(),
      summary: `Proposal payload applied: ${proposal.title} (${Object.keys(payload).join(", ")})`,
      alignment: this.lastEvaluation?.alignment,
    });
  }

  private processDeferredEffectChecks(): void {
    if (this.deferredEffectChecks.length === 0) return;
    const currentAlignment = this.lastEvaluation?.alignment ?? 0;
    const remaining: typeof this.deferredEffectChecks = [];

    for (const check of this.deferredEffectChecks) {
      if (this.tickCounter >= check.checkAfterTick) {
        const entry = this.proposalHistory.find(h => h.id === check.proposalId);
        if (entry) {
          entry.effectAfter = currentAlignment;
          entry.effectDelta = currentAlignment - check.baseline;
        }
      } else {
        remaining.push(check);
      }
    }
    this.deferredEffectChecks = remaining;
  }

  denyDaedalusProposal(proposalId: string): DaedalusProposal | null {
    let proposal: DaedalusProposal | null = null;

    if (this.surfacedProposal?.id === proposalId) {
      proposal = this.surfacedProposal;
      this.surfacedProposal = null;
    } else {
      const idx = this.deferredProposals.findIndex(p => p.id === proposalId);
      if (idx >= 0) {
        proposal = this.deferredProposals[idx];
        this.deferredProposals.splice(idx, 1);
      }
    }
    if (!proposal) return null;

    proposal.status = "denied";
    proposal.resolvedAt = Date.now();
    this.recordProposalHistory(proposal);
    getDaedalusEventBus().publish({
      type: "DAEDALUS_PROPOSAL_DENIED",
      timestamp: nowIso(),
      summary: `Operator denied: ${proposal.title}`,
      alignment: this.lastEvaluation?.alignment,
    });

    this.lastResolutionAt = Date.now();
    this.reEvaluateDeferredProposals();
    this.surfaceNextProposal();

    return proposal;
  }

  submitChangeProposal(proposal: ChangeProposal): ApprovalDecision {
    const evaluation = this.lastEvaluation ?? this.evaluate() as StrategyEvaluation;
    const safeMode = getSafeModeState();
    const decision = shouldAutoApprove(proposal, evaluation, safeMode, this.alignmentConfig);

    const bus = getDaedalusEventBus();
    if (decision.autoApprove) {
      bus.publish({
        type: "CHANGE_AUTO_APPROVED",
        timestamp: nowIso(),
        summary: `Change auto-approved: ${proposal.description} (alignment ${decision.alignment}%, confidence ${decision.confidence}%)`,
        alignment: decision.alignment,
      });
    } else {
      const failedAxes = Object.entries(decision.reasons)
        .filter(([, v]) => !v)
        .map(([k]) => k)
        .join(", ");
      bus.publish({
        type: "CHANGE_REQUIRES_REVIEW",
        timestamp: nowIso(),
        summary: `Change requires review: ${proposal.description} — failed: ${failedAxes}`,
        alignment: decision.alignment,
      });

      const pendingOp: OperatorPendingProposal = {
        id: `op-${Date.now()}-${Math.random().toString(36).slice(2, 5)}`,
        kind: proposal.kind,
        description: proposal.description,
        payload: proposal.payload ?? {},
        decision,
        createdAt: Date.now(),
        status: "pending_review",
      };
      this.operatorPendingProposals.push(pendingOp);
      if (this.operatorPendingProposals.length > MAX_OPERATOR_PENDING) {
        this.operatorPendingProposals = this.operatorPendingProposals.slice(-MAX_OPERATOR_PENDING);
      }
    }

    return decision;
  }

  forceApproveOperatorProposal(id: string): OperatorPendingProposal | null {
    const proposal = this.operatorPendingProposals.find(p => p.id === id && p.status === "pending_review");
    if (!proposal) return null;
    proposal.status = "force_approved";
    proposal.resolvedAt = Date.now();
    getDaedalusEventBus().publish({
      type: "CHANGE_AUTO_APPROVED",
      timestamp: nowIso(),
      summary: `Operator force-approved: ${proposal.description}`,
      alignment: this.lastEvaluation?.alignment,
    });
    return proposal;
  }

  withdrawOperatorProposal(id: string): OperatorPendingProposal | null {
    const proposal = this.operatorPendingProposals.find(p => p.id === id && p.status === "pending_review");
    if (!proposal) return null;
    proposal.status = "withdrawn";
    proposal.resolvedAt = Date.now();
    return proposal;
  }

  getApprovalGateConfig(): ApprovalGateConfig {
    return getApprovalGateConfig();
  }

  updateApprovalGateConfig(patch: Partial<ApprovalGateConfig>): ApprovalGateConfig {
    return updateApprovalGateConfig(patch);
  }

  getRecentApprovals(): ApprovalDecision[] {
    return getRecentApprovalDecisions();
  }

  getRegulationConfig(): RegulationConfig {
    return getRegulationConfig();
  }

  updateRegulationConfig(patch: Partial<RegulationConfig>): RegulationConfig {
    return updateRegulationConfig(patch);
  }

  getLastRegulationOutput(): RegulationOutput | null {
    return getLastRegulationOutput();
  }

  classifyChange(input: ChangeImpactInput) {
    return classifyChange(input);
  }

  registerTrackedChange(
    record: Omit<AppliedChangeRecord, "status" | "appliedAtTick">,
    rollbackFn?: () => void,
  ): AppliedChangeRecord {
    const result = registerChange(record, rollbackFn);
    getDaedalusEventBus().publish({
      type: "CHANGE_REGISTERED",
      timestamp: nowIso(),
      summary: `Change registered: ${result.description} (impact: ${result.impact}, window: ${result.evaluationWindow} ticks)`,
    });
    return result;
  }

  getRollbackRegistrySnapshot(): RollbackRegistrySnapshot {
    return getRollbackRegistrySnapshot();
  }

  getActiveTrackedChanges(): AppliedChangeRecord[] {
    return getActiveChanges();
  }

  getRecentRollbackEvents(): RollbackEvent[] {
    return getRecentRollbacks();
  }

  getRollbackConfig() {
    return getRollbackConfig();
  }

  updateRollbackConfig(patch: Record<string, number | boolean>) {
    return updateRollbackConfig(patch);
  }

  // ── Operator Identity ───────────────────────────────────────────

  bindOperatorProfile(profile: OperatorProfile): OperatorTrustState {
    const state = bindOperator(profile);
    getDaedalusEventBus().publish({
      type: "OPERATOR_BOUND",
      timestamp: nowIso(),
      summary: `Operator '${profile.displayName}' (${profile.id}) bound to Daedalus`,
    });
    return state;
  }

  unbindCurrentOperator(): OperatorTrustState {
    const state = unbindOperator();
    getDaedalusEventBus().publish({
      type: "OPERATOR_UNBOUND",
      timestamp: nowIso(),
      summary: "Operator unbound from Daedalus",
    });
    return state;
  }

  submitOperatorObservation(obs: OperatorObservation) {
    const result = updateOperatorTrust(obs);
    if (result.suspicious) {
      getDaedalusEventBus().publish({
        type: "OPERATOR_TRUST_SUSPICIOUS",
        timestamp: nowIso(),
        summary: `Suspicious operator activity detected at tick ${obs.tick} (trust: ${result.state.trustScore})`,
      });
    }
    if (obs.signals.highRiskRequest && !result.allowHighRiskActions) {
      getDaedalusEventBus().publish({
        type: "OPERATOR_HIGH_RISK_DENIED",
        timestamp: nowIso(),
        summary: `High-risk request denied at tick ${obs.tick} (trust: ${result.state.trustScore}, posture: ${result.state.boundOperator ? "bound" : "unbound"})`,
      });
    }
    return result;
  }

  getOperatorTrustSnapshot(): OperatorTrustCockpitSnapshot {
    return getOperatorTrustSnapshot();
  }

  getOperatorTrustState(): OperatorTrustState {
    return getOperatorTrustState();
  }

  getRecentHighRiskLog() {
    return getRecentHighRiskLog();
  }

  checkHighRisk(action: string) {
    return isHighRiskAction(action);
  }

  gateHighRiskAction(action: string): { allowed: boolean; reasons: string[] } {
    const reasons: string[] = [];
    const freezeState = getConstitutionalFreezeState();
    if (freezeState.frozen) {
      reasons.push(`constitutional_freeze: ${freezeState.reason}`);
      return { allowed: false, reasons };
    }
    if (!isHighRiskAction(action)) return { allowed: true, reasons: [] };
    const trustSnap = getOperatorTrustSnapshot();
    if (!trustSnap.boundOperatorId) reasons.push("no_bound_operator");
    if (trustSnap.trustScore < 85) reasons.push("trust_below_threshold");
    if (trustSnap.posture === "hostile_or_unknown") reasons.push("hostile_posture");
    if (trustSnap.posture === "cautious") reasons.push("cautious_posture");
    const allowed = reasons.length === 0;
    const obs = { tick: this.tickCounter, signals: { credentialsValid: true, deviceKnown: true, deviceSuspicious: false, behaviorMatchScore: 80, continuityMatchScore: 80, highRiskRequest: true } };
    const trustResult = { state: getOperatorTrustState(), allowHighRiskActions: allowed, suspicious: !allowed };
    buildHighRiskDecisionLog(this.tickCounter, action, obs, trustResult);
    if (!allowed) {
      getDaedalusEventBus().publish({
        type: "OPERATOR_HIGH_RISK_DENIED",
        timestamp: nowIso(),
        summary: `High-risk action '${action}' denied: ${reasons.join(", ")}`,
      });
    }
    return { allowed, reasons };
  }

  setConstitutionalFreeze(reason: string) {
    const freeze = enableConstitutionalFreeze(reason);
    getDaedalusEventBus().publish({
      type: "CONSTITUTIONAL_FREEZE_CHANGED",
      timestamp: nowIso(),
      summary: `Constitutional freeze enabled: ${reason}`,
    });
    return freeze;
  }

  clearConstitutionalFreeze() {
    const freeze = disableConstitutionalFreeze();
    getDaedalusEventBus().publish({
      type: "CONSTITUTIONAL_FREEZE_CHANGED",
      timestamp: nowIso(),
      summary: "Constitutional freeze disabled",
    });
    return freeze;
  }

  getConstitutionalFreezeState() {
    return getConstitutionalFreezeState();
  }

  startOperatorAttunement() {
    return startAttunement();
  }

  advanceOperatorAttunement() {
    return advanceAttunement();
  }

  getOperatorAttunementState() {
    return getAttunementState();
  }

  getOperatorIntrospection() {
    return introspectPosture();
  }

  getOperatorTimeline() {
    return getRelationshipTimeline();
  }

  getOperatorTrustDrift() {
    return getTrustDriftSamples();
  }

  private buildContext(): AlignmentContext {
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;
    const behavioral = computeBehavioralField(beingMap);
    const constitutionReport = validateBeingConstitution(beings, [], behavioral.dominantBeingId);

    const postureSnapshot = governanceService.getPostureSnapshot();
    const overrides = governanceService.listOverrides();
    const drifts = governanceService.listDrifts();
    const votes = governanceService.listVotes();

    const registry = getNodeMirrorRegistry();
    const views = registry.toCockpitView();
    const quarantinedCount = views.filter(v => v.status === "quarantined").length;
    const totalErrors = views.reduce((sum, v) => sum + v.errorCount, 0);
    const activeHeartbeats = views.filter(v => v.lastHeartbeatAt !== null).length;

    return {
      beings,
      constitutionReport,
      posture: postureSnapshot.posture,
      postureReason: postureSnapshot.reason,
      overrides,
      drifts,
      votes,
      nodeCount: views.length,
      quarantinedCount,
      totalErrors,
      activeHeartbeats,
    };
  }
}

export const strategyService = new StrategyService();
