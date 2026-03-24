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

class StrategyService {
  private lastEvaluation: StrategyEvaluation | null = null;
  private lastStrategyName: StrategyName | null = null;
  private lastTickResult: KernelTickResult | null = null;
  private kernelConfig: KernelRuntimeConfig = { ...DEFAULT_KERNEL_CONFIG };
  private alignmentConfig: AlignmentConfig = { ...DEFAULT_ALIGNMENT_CONFIG };
  private prevAcceptedCount = 0;

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
