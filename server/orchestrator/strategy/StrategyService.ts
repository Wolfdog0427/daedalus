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

    if (tick.regulation.shouldEnterSafeMode || tick.regulation.shouldPauseAutonomy) {
      getDaedalusEventBus().publish({
        type: "REGULATION_SAFE_MODE_SIGNAL",
        timestamp: nowIso(),
        summary: `Regulation governance: ${tick.regulation.shouldEnterSafeMode ? "enter safe mode" : ""}${tick.regulation.shouldPauseAutonomy ? " pause autonomy" : ""}`.trim(),
        alignment: tick.strategy.alignment,
      });
    }

    this.lastStrategyName = tick.strategy.name;
    this.lastEvaluation = tick.strategy;
    this.lastTickResult = tick;

    this.generateDaedalusProposals(tick);

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
    const mark = (kind: string) => this.lastProposalKindTick.set(kind, this.tickCounter);

    // ── Alignment & Governance Proposals ──────────────────────────

    if (eval_.alignment < 80 && !pendingIds.has("alignment_boost") && !safeMode.active && cooldown("alignment_boost", 20)) {
      mark("alignment_boost");
      this.createDaedalusProposal({
        kind: "alignment_boost",
        title: "Increase governance strictness",
        description: `Alignment is at ${eval_.alignment}%. Daedalus recommends tightening governance strictness to stabilize.`,
        rationale: `Current alignment (${eval_.alignment}%) is below the target of 92%. Increasing governance strictness from ${this.kernelConfig.governanceStrictness?.toFixed(2) ?? "0.80"} will help prevent further drift.`,
        impact: "medium",
        touchesInvariants: false,
        reversible: true,
        payload: { governanceStrictness: Math.min(1, (this.kernelConfig.governanceStrictness ?? 0.8) + 0.05) },
        eval_,
      });
    }

    if (regulation.telemetry.appliedMacro && !pendingIds.has("regulation_tune") && cooldown("regulation_tune", 15)) {
      mark("regulation_tune");
      this.createDaedalusProposal({
        kind: "regulation_tune",
        title: "Adjust regulation damping",
        description: `Macro-correction fired (${regulation.telemetry.reason}). Daedalus recommends adjusting damping to reduce oscillation.`,
        rationale: `The regulation loop applied a macro-correction of ${regulation.telemetry.macroDampedCorrection.toFixed(2)}. Increasing macro damping will smooth future corrections.`,
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { macroDamping: 0.75 },
        eval_,
      });
    }

    if (eval_.confidence < 70 && !pendingIds.has("sensitivity_reduction") && cooldown("sensitivity_reduction", 20)) {
      mark("sensitivity_reduction");
      this.createDaedalusProposal({
        kind: "sensitivity_reduction",
        title: "Reduce strategy sensitivity",
        description: `Confidence is low (${eval_.confidence}%). Daedalus recommends reducing strategy sensitivity to avoid unstable decisions.`,
        rationale: `Low confidence suggests the system is uncertain about its strategy. Reducing sensitivity from ${this.kernelConfig.strategySensitivity?.toFixed(2) ?? "1.00"} will make strategy selection more conservative.`,
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { strategySensitivity: Math.max(0.5, (this.kernelConfig.strategySensitivity ?? 1.0) - 0.1) },
        eval_,
      });
    }

    if (safeMode.active && !pendingIds.has("safe_mode_recovery") && cooldown("safe_mode_recovery", 30)) {
      mark("safe_mode_recovery");
      this.createDaedalusProposal({
        kind: "safe_mode_recovery",
        title: "Safe mode recovery plan",
        description: `System is in safe mode (${safeMode.reason ?? "alignment critically low"}). Daedalus recommends a recovery configuration.`,
        rationale: "Safe mode indicates critical alignment failure. This proposal applies conservative settings to stabilize the system before exiting safe mode.",
        impact: "high",
        touchesInvariants: true,
        reversible: true,
        payload: { governanceStrictness: 0.95, strategySensitivity: 0.6 },
        eval_,
      });
    }

    const drift = tick.drift;
    if (drift.drifting && !pendingIds.has("drift_correction") && cooldown("drift_correction", 20)) {
      mark("drift_correction");
      this.createDaedalusProposal({
        kind: "drift_correction",
        title: "Correct alignment drift",
        description: `Alignment drift detected (Δ${drift.delta?.toFixed(1)}). Daedalus recommends a correction.`,
        rationale: `Alignment is drifting downward by ${Math.abs(drift.delta ?? 0).toFixed(1)} points over the measurement window. Raising the alignment floor will trigger earlier self-correction.`,
        impact: "medium",
        touchesInvariants: false,
        reversible: true,
        payload: { alignmentFloor: Math.min(80, (this.alignmentConfig.alignmentFloor ?? 60) + 5) },
        eval_,
      });
    }

    // ── Self-Improvement & New Capability Proposals ───────────────

    // After surviving safe mode, propose resilience improvements
    if (this.safeModeStreak === 0 && this.tickCounter > 5) {
      const recentSafeModeRecovery = this.proposalHistory.some(
        p => p.kind === "safe_mode_recovery" && p.status === "approved" && Date.now() - p.resolvedAt < 60_000,
      );
      if (recentSafeModeRecovery && !pendingIds.has("resilience_upgrade") && cooldown("resilience_upgrade", 50)) {
        mark("resilience_upgrade");
        this.createDaedalusProposal({
          kind: "resilience_upgrade",
          title: "Strengthen post-crisis resilience",
          description: "Daedalus recently recovered from safe mode. I propose tightening the alignment floor and reducing sensitivity to prevent re-entry.",
          rationale: "Post-crisis analysis: the system entered safe mode and recovered. Preemptively raising the floor and reducing sensitivity will create a larger buffer against future crises.",
          impact: "medium",
          touchesInvariants: false,
          reversible: true,
          payload: { alignmentFloor: Math.min(80, (this.alignmentConfig.alignmentFloor ?? 60) + 3), strategySensitivity: Math.max(0.6, (this.kernelConfig.strategySensitivity ?? 1) - 0.05) },
          eval_,
        });
      }
    }

    // When stable for a sustained period, propose capability expansion
    if (this.stableStreak >= 30 && !pendingIds.has("capability_expansion") && cooldown("capability_expansion", 100)) {
      mark("capability_expansion");
      this.createDaedalusProposal({
        kind: "capability_expansion",
        title: "Expand autonomous capabilities",
        description: "The system has been stable (alignment ≥88%, confidence ≥80%) for a sustained period. Daedalus proposes expanding autonomous decision-making capabilities.",
        rationale: `${this.stableStreak} consecutive stable ticks demonstrate the system can be trusted with broader autonomy. This enables auto-approval of low-impact changes and expands the intent recognition vocabulary.`,
        impact: "medium",
        touchesInvariants: false,
        reversible: true,
        payload: { enableExpandedAutonomy: true, stableTicksAtProposal: this.stableStreak },
        eval_,
      });
    }

    // Propose monitoring improvements when alignment oscillates
    const history = this.proposalHistory.filter(p => Date.now() - p.resolvedAt < 300_000);
    const driftCorrections = history.filter(p => p.kind === "drift_correction").length;
    if (driftCorrections >= 2 && !pendingIds.has("monitoring_enhancement") && cooldown("monitoring_enhancement", 80)) {
      mark("monitoring_enhancement");
      this.createDaedalusProposal({
        kind: "monitoring_enhancement",
        title: "Enhance drift monitoring precision",
        description: `${driftCorrections} drift corrections in the recent window suggest alignment is oscillating. Daedalus proposes narrowing the drift detection window for earlier intervention.`,
        rationale: "Repeated drift corrections indicate the current detection window may be too wide, allowing drift to accumulate before intervention. Tightening the window enables smoother micro-corrections and reduces the need for macro-corrections.",
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { driftWindowReduction: true, proposedDriftThreshold: 8 },
        eval_,
      });
    }

    // Propose architectural improvements when rollback count is high
    const recentRollbacks = tick.rollbacks.length;
    if (recentRollbacks >= 2 && !pendingIds.has("architecture_improvement") && cooldown("architecture_improvement", 60)) {
      mark("architecture_improvement");
      this.createDaedalusProposal({
        kind: "architecture_improvement",
        title: "Improve change evaluation architecture",
        description: `${recentRollbacks} rollbacks occurred this tick. Daedalus proposes extending the change evaluation window and tightening the degradation threshold.`,
        rationale: "Multiple rollbacks indicate changes are being applied that degrade alignment. A longer evaluation window and stricter degradation threshold will catch harmful changes earlier.",
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { evaluationWindowExtension: 50, degradationThresholdReduction: 2 },
        eval_,
      });
    }

    // Propose learning from successful patterns when many proposals have been approved
    const approvedRecent = history.filter(p => p.status === "approved" || p.status === "auto_approved");
    if (approvedRecent.length >= 3 && !pendingIds.has("pattern_learning") && cooldown("pattern_learning", 120)) {
      const avgDelta = approvedRecent.reduce((s, p) => s + (p.effectDelta ?? 0), 0) / approvedRecent.length;
      if (avgDelta > 0) {
        mark("pattern_learning");
        this.createDaedalusProposal({
          kind: "pattern_learning",
          title: "Codify successful improvement patterns",
          description: `${approvedRecent.length} recent proposals improved alignment by an average of ${avgDelta.toFixed(1)}%. Daedalus proposes codifying these patterns for automatic future application.`,
          rationale: "Repeated successful proposals of similar types suggest a stable improvement pattern. Codifying this allows Daedalus to apply similar corrections automatically when conditions recur, reducing operator overhead.",
          impact: "medium",
          touchesInvariants: false,
          reversible: true,
          payload: { codifyPatterns: true, patternCount: approvedRecent.length, avgEffectDelta: avgDelta },
          eval_,
        });
      }
    }

    // Propose communication improvement when operator trust is below threshold
    if (tick.operatorTrust.trustScore < 60 && tick.operatorTrust.boundOperatorId && !pendingIds.has("trust_recovery_protocol") && cooldown("trust_recovery_protocol", 40)) {
      mark("trust_recovery_protocol");
      this.createDaedalusProposal({
        kind: "trust_recovery_protocol",
        title: "Initiate trust recovery protocol",
        description: `Operator trust is at ${tick.operatorTrust.trustScore}%. Daedalus proposes increasing transparency and requiring explicit confirmation for all changes until trust stabilizes.`,
        rationale: `Trust score ${tick.operatorTrust.trustScore}% (posture: ${tick.operatorTrust.posture}) indicates the operator-Daedalus relationship needs reinforcement. Increasing confirmation requirements and providing richer explanations will help rebuild trust.`,
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { requireExplicitConfirmation: true, enhancedExplanations: true, trustAtProposal: tick.operatorTrust.trustScore },
        eval_,
      });
    }

    // Propose new node capability when fleet is healthy but small
    const nodeCount = this.buildContext().nodeCount;
    if (nodeCount < 3 && eval_.alignment >= 85 && !pendingIds.has("fleet_expansion") && cooldown("fleet_expansion", 100)) {
      mark("fleet_expansion");
      this.createDaedalusProposal({
        kind: "fleet_expansion",
        title: "Recommend fleet expansion",
        description: `Only ${nodeCount} node(s) active. Daedalus recommends expanding the fleet for better resilience and distributed governance.`,
        rationale: `A fleet of ${nodeCount} node(s) has limited fault tolerance. Adding nodes improves heartbeat coverage, distributes governance load, and increases the system's ability to survive node failures.`,
        impact: "medium",
        touchesInvariants: false,
        reversible: true,
        payload: { recommendedNodeCount: Math.max(5, nodeCount + 2), currentNodeCount: nodeCount },
        eval_,
      });
    }

    // Propose self-assessment ritual when system has been running a while without one
    if (this.tickCounter > 0 && this.tickCounter % 200 === 0 && !pendingIds.has("self_assessment") && cooldown("self_assessment", 200)) {
      mark("self_assessment");
      const approvedCount = this.proposalHistory.filter(p => p.status === "approved" || p.status === "auto_approved").length;
      const deniedCount = this.proposalHistory.filter(p => p.status === "denied").length;
      this.createDaedalusProposal({
        kind: "self_assessment",
        title: "Periodic self-assessment report",
        description: `Daedalus has run for ${this.tickCounter} ticks. Proposals: ${approvedCount} approved, ${deniedCount} denied. Current alignment: ${eval_.alignment}%, confidence: ${eval_.confidence}%.`,
        rationale: `Regular self-assessment helps maintain awareness of the system's trajectory. Over ${this.tickCounter} ticks, Daedalus has proposed ${this.proposalHistory.length} changes. This ritual confirms the operator is aware of the system's current state and trajectory.`,
        impact: "low",
        touchesInvariants: false,
        reversible: true,
        payload: { tickCount: this.tickCounter, totalProposals: this.proposalHistory.length, approvedCount, deniedCount, currentAlignment: eval_.alignment, currentConfidence: eval_.confidence },
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
    eval_: StrategyEvaluation;
  }): void {
    if (this.pendingDaedalusProposals.length >= MAX_PENDING_PROPOSALS) return;

    const autoApprovable =
      opts.eval_.alignment >= 95 &&
      opts.eval_.confidence >= 80 &&
      opts.impact === "low" &&
      !opts.touchesInvariants &&
      opts.reversible;

    const proposal: DaedalusProposal = {
      id: `dp-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      kind: opts.kind,
      title: opts.title,
      description: opts.description,
      rationale: opts.rationale,
      alignment: opts.eval_.alignment,
      confidence: opts.eval_.confidence,
      impact: opts.impact,
      touchesInvariants: opts.touchesInvariants,
      reversible: opts.reversible,
      autoApprovable,
      payload: opts.payload,
      createdAt: Date.now(),
      status: autoApprovable ? "auto_approved" : "pending",
      effectBaseline: opts.eval_.alignment,
    };

    if (autoApprovable) {
      proposal.resolvedAt = Date.now();
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
        summary: `Daedalus proposes: ${opts.title} (alignment ${opts.eval_.alignment}%, impact ${opts.impact})`,
        alignment: opts.eval_.alignment,
      });
    }
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

  approveDaedalusProposal(proposalId: string): DaedalusProposal | null {
    const idx = this.pendingDaedalusProposals.findIndex(p => p.id === proposalId);
    if (idx < 0) return null;
    const proposal = this.pendingDaedalusProposals[idx];
    proposal.status = "approved";
    proposal.resolvedAt = Date.now();
    proposal.effectAfter = this.lastEvaluation?.alignment ?? undefined;
    this.pendingDaedalusProposals.splice(idx, 1);
    this.recordProposalHistory(proposal);
    getDaedalusEventBus().publish({
      type: "DAEDALUS_PROPOSAL_APPROVED",
      timestamp: nowIso(),
      summary: `Operator approved: ${proposal.title}`,
      alignment: this.lastEvaluation?.alignment,
    });
    return proposal;
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
