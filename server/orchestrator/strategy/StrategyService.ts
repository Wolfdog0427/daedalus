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
  payload: Record<string, unknown>;
  parameterChanges: ProposalParameterChange[];
  operatorImpact: string;
  boundaries: string[];
  createdAt: number;
  status: "pending" | "approved" | "denied" | "expired" | "auto_approved";
  resolvedAt?: number;
  effectBaseline?: number;
  effectAfter?: number;
}

export interface ProposalHistoryEntry {
  id: string;
  title: string;
  kind: string;
  status: "approved" | "denied" | "auto_approved" | "expired";
  alignment: number;
  confidence: number;
  impact: "low" | "medium" | "high";
  effectBaseline: number | null;
  effectAfter: number | null;
  effectDelta: number | null;
  createdAt: number;
  resolvedAt: number;
}

const MAX_PENDING_PROPOSALS = 10;
const MAX_PROPOSAL_HISTORY = 50;
const PROPOSAL_EXPIRE_MS = 15 * 60 * 1000;

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
  private pendingDaedalusProposals: DaedalusProposal[] = [];
  private proposalHistory: ProposalHistoryEntry[] = [];

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
    this.expireStalePendingProposals();
    this.tickCounter++;

    const eval_ = tick.strategy;
    const safeMode = tick.safeMode;
    const regulation = tick.regulation;
    const pendingIds = new Set(this.pendingDaedalusProposals.map(p => p.kind));

    if (safeMode.active) this.safeModeStreak++;
    else this.safeModeStreak = 0;

    if (eval_.alignment >= 88 && eval_.confidence >= 80) this.stableStreak++;
    else this.stableStreak = 0;

    const cooldown = (kind: string, minTicks: number) => {
      const last = this.lastProposalKindTick.get(kind) ?? -Infinity;
      return this.tickCounter - last >= minTicks;
    };
    const queueHasRoom = () => this.pendingDaedalusProposals.length < MAX_PENDING_PROPOSALS;
    const mark = (kind: string) => this.lastProposalKindTick.set(kind, this.tickCounter);

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
      const currentAutoApprovalThreshold = 95;
      const proposedAutoApprovalThreshold = 93;
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
        operatorImpact: "Daedalus will revert applied changes faster if they degrade alignment (at ${proposedDegThreshold} points instead of ${currentDegThreshold}). No change to operator authority or approval requirements.",
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
    if (this.pendingDaedalusProposals.length >= MAX_PENDING_PROPOSALS) return;

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
    const autoApprovable =
      opts.eval_.alignment >= gateConfig.alignmentThreshold &&
      opts.eval_.confidence >= gateConfig.confidenceThreshold &&
      classifiedImpact === "low" &&
      !classifiedTouchesInvariants &&
      opts.reversible &&
      (!safeMode.active || gateConfig.allowDuringSafeMode) &&
      !this.autonomyPaused;

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
      payload: opts.payload,
      parameterChanges: opts.parameterChanges,
      operatorImpact: opts.operatorImpact,
      boundaries: opts.boundaries,
      createdAt: Date.now(),
      status: autoApprovable ? "auto_approved" : "pending",
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
      this.pendingDaedalusProposals.push(proposal);
      getDaedalusEventBus().publish({
        type: "DAEDALUS_PROPOSAL_CREATED",
        timestamp: nowIso(),
        summary: `Daedalus proposes: ${opts.title} (alignment ${opts.eval_.alignment}%, impact ${classifiedImpact})`,
        alignment: opts.eval_.alignment,
      });
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

  private expireStalePendingProposals(): void {
    const now = Date.now();
    const expired: DaedalusProposal[] = [];
    this.pendingDaedalusProposals = this.pendingDaedalusProposals.filter(p => {
      if (now - p.createdAt > PROPOSAL_EXPIRE_MS) {
        p.status = "expired";
        p.resolvedAt = now;
        expired.push(p);
        return false;
      }
      return true;
    });
    for (const p of expired) this.recordProposalHistory(p);
  }

  private recordProposalHistory(proposal: DaedalusProposal): void {
    const effectAfter = this.lastEvaluation?.alignment ?? null;
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
      effectDelta: (proposal.effectBaseline != null && effectAfter != null)
        ? effectAfter - proposal.effectBaseline
        : null,
      createdAt: proposal.createdAt,
      resolvedAt: proposal.resolvedAt ?? Date.now(),
    };
    this.proposalHistory.push(entry);
    if (this.proposalHistory.length > MAX_PROPOSAL_HISTORY) {
      this.proposalHistory = this.proposalHistory.slice(-MAX_PROPOSAL_HISTORY);
    }
  }

  getPendingDaedalusProposals(): DaedalusProposal[] {
    this.expireStalePendingProposals();
    return [...this.pendingDaedalusProposals];
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
    const idx = this.pendingDaedalusProposals.findIndex(p => p.id === proposalId);
    if (idx < 0) return null;
    const proposal = this.pendingDaedalusProposals[idx];
    proposal.status = "approved";
    proposal.resolvedAt = Date.now();
    proposal.effectBaseline = this.lastEvaluation?.alignment ?? undefined;
    this.pendingDaedalusProposals.splice(idx, 1);

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
    return proposal;
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
    const idx = this.pendingDaedalusProposals.findIndex(p => p.id === proposalId);
    if (idx < 0) return null;
    const proposal = this.pendingDaedalusProposals[idx];
    proposal.status = "denied";
    proposal.resolvedAt = Date.now();
    this.pendingDaedalusProposals.splice(idx, 1);
    this.recordProposalHistory(proposal);
    getDaedalusEventBus().publish({
      type: "DAEDALUS_PROPOSAL_DENIED",
      timestamp: nowIso(),
      summary: `Operator denied: ${proposal.title}`,
      alignment: this.lastEvaluation?.alignment,
    });
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
    }

    return decision;
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
