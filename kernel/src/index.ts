/**
 * Daedalus Kernel entrypoint.
 *
 * The kernel is the "thinking" layer — it hosts the strategy dispatcher,
 * alignment telemetry, self-correction loop, posture selector, drift
 * detector, strategy gating, escalation, safe mode, and intent interpreter.
 *
 * The primary entry point for the orchestrator is `tickKernel`, which
 * runs the full pipeline:
 *   self-correction → strategy dispatch (gate + escalate + safe mode)
 *     → posture (+ safe mode overlay) → drift detection → intent
 */

import { selectStrategy, getLastStrategyName, getLastEscalation, resetDispatcher } from "./dispatcher";
import { kernelTelemetry } from "./telemetry";
import { applySelfCorrectionIfNeeded, computeRecentAlignmentTrend } from "./selfCorrection";
import { selectPosture } from "./posture";
import { detectAlignmentDrift } from "./driftDetector";
import { interpretIntent, type IntentInput } from "./intent";
import { getSafeModeState } from "./safeMode";
import { evaluateProposals } from "./autoApproval";
import { runRegulation, applyRegulationToPosture } from "./regulationLoop";
import { processRollbacks } from "./rollbackRegistry";
import { getOperatorTrustSnapshot, recordTrustDriftSample } from "./operatorIdentity";
import type {
  AlignmentContext,
  KernelRuntimeConfig,
  KernelTickResult,
  IntentInterpretation,
  ChangeProposal,
  ApprovalDecision,
  AlignmentConfig,
  RegulationConfig,
  RollbackEvent,
  OperatorTrustCockpitSnapshot,
} from "./types";
import { DEFAULT_KERNEL_CONFIG } from "./types";

export function tickKernel(
  context: AlignmentContext,
  config: KernelRuntimeConfig = { ...DEFAULT_KERNEL_CONFIG },
  intentInput?: IntentInput,
  changeProposals?: ChangeProposal[],
  alignmentConfig?: AlignmentConfig,
  regulationCfg?: RegulationConfig,
): KernelTickResult {
  // Single history read per tick — reused by all downstream consumers
  const history = kernelTelemetry.getAlignmentHistory();

  // Self-correction adjusts config for NEXT tick (returned via result.config).
  // Strategy evaluation does not consume KernelRuntimeConfig directly, so
  // the one-tick delay is intentional and documented here.
  const correction = applySelfCorrectionIfNeeded(config, history);
  const adjustedConfig = correction.config;

  const strategy = selectStrategy(context);

  const basePosture = selectPosture(strategy);

  const drift = detectAlignmentDrift(history);

  const escalation = getLastEscalation();

  const safeMode = getSafeModeState();

  const autonomyPaused = escalation.level === "critical" ||
    strategy.name === "autonomy_paused_alignment_critical";

  const regulation = runRegulation(
    history,
    strategy.alignment,
    safeMode,
    autonomyPaused,
    regulationCfg,
  );

  const posture = applyRegulationToPosture(basePosture, regulation);

  let intent: IntentInterpretation | null = null;
  if (intentInput) {
    intent = interpretIntent(intentInput, {
      avgAlignment: correction.trend.avgAlignment,
    });
  }

  let approvals: ApprovalDecision[] = [];
  if (changeProposals && changeProposals.length > 0) {
    approvals = evaluateProposals(changeProposals, strategy, safeMode, alignmentConfig);
  }

  const rollbacks = processRollbacks(strategy.alignment);

  recordTrustDriftSample(history.length);

  const operatorTrust = getOperatorTrustSnapshot();

  return {
    strategy,
    posture,
    config: adjustedConfig,
    drift,
    trend: correction.trend,
    selfCorrected: correction.corrected,
    escalation,
    safeMode,
    intent,
    approvals,
    regulation,
    rollbacks,
    operatorTrust,
  };
}

export { selectStrategy, getLastStrategyName, getLastEscalation, resetDispatcher };
export { evaluateStrategy, computeAlignmentBreakdown, explainStrategy } from "./strategy";
export { kernelTelemetry } from "./telemetry";
export { gateStrategyByAlignment, resetGateBand } from "./strategyGate";
export { applySelfCorrectionIfNeeded, computeRecentAlignmentTrend, setOperatorConfigBaseline } from "./selfCorrection";
export { selectPosture } from "./posture";
export { detectAlignmentDrift } from "./driftDetector";
export { computeAlignmentEscalation, resetEscalation } from "./escalation";
export { interpretIntent, resetIntentState } from "./intent";
export { computeIdentityContinuity, resetIdentityState, getLastIdentitySnapshot } from "./identity";
export {
  getSafeModeState,
  updateSafeModeFromAlignment,
  applySafeModeToPosture,
  resetSafeMode,
} from "./safeMode";
export {
  shouldAutoApprove,
  evaluateProposals,
  getApprovalGateConfig,
  updateApprovalGateConfig,
  getRecentApprovalDecisions,
  resetApprovalGate,
} from "./autoApproval";
export {
  bindOperator,
  unbindOperator,
  updateOperatorTrust,
  classifyTrustPosture,
  deriveComfortPosture,
  isHighRiskAction,
  buildHighRiskDecisionLog,
  buildComfortLayerView,
  enableConstitutionalFreeze,
  disableConstitutionalFreeze,
  getConstitutionalFreezeState,
  enforceConstitutionalFreeze,
  computeContinuitySeal,
  verifyContinuitySeal,
  runSelfAudit,
  introspectHighRiskDecision,
  introspectPosture,
  startAttunement,
  advanceAttunement,
  getAttunementState,
  recordTrustDriftSample,
  getTrustDriftSamples,
  buildWeeklyTrustNarrative,
  addRelationshipEvent,
  getRelationshipTimeline,
  runRedTeamScenario,
  runFutureYouSanityCheck,
  enforceNoSilentDrift,
  getOperatorTrustSnapshot,
  getOperatorTrustState,
  getRecentHighRiskLog,
  resetOperatorIdentity,
} from "./operatorIdentity";
export {
  classifyChangeImpact,
  detectInvariantTouchBySurface,
  classifyChange,
} from "./changeClassifier";
export {
  registerChange,
  evaluateChangeOutcome,
  processRollbacks,
  getRollbackRegistrySnapshot,
  getActiveChanges,
  getRecentRollbacks,
  getCurrentTick,
  getRollbackConfig,
  updateRollbackConfig,
  resetRollbackRegistry,
} from "./rollbackRegistry";
export {
  regulateAlignment,
  runRegulation,
  computeDriftMetrics,
  applyRegulationToPosture,
  getRegulationConfig,
  updateRegulationConfig,
  getLastRegulationOutput,
  resetRegulationState,
} from "./regulationLoop";

export type {
  AlignmentPolicy,
  KernelConfig,
  BeingDescriptor,
  StrategyTelemetryEntry,
  KernelTelemetrySnapshot,
  AlignmentBreakdown,
  StrategyName,
  StrategyEvaluation,
  AlignmentContext,
  GatedStrategyName,
  SharedStrategyName,
  SharedStrategyEvaluation,
  AlignmentHistoryPoint,
  AlignmentDriftResult,
  KernelRuntimeConfig,
  AlignmentTrend,
  KernelPosture,
  KernelTickResult,
  EscalationLevel,
  EscalationResult,
  SafeModeState,
  AlignmentConfig,
  AlignmentEventKind,
  AlignmentEvent,
  IntentInterpretation,
  ChangeProposal,
  ChangeProposalKind,
  ChangeImpact,
  ApprovalDecision,
  ApprovalReasonBreakdown,
  ApprovalGateConfig,
  DriftMetrics,
  RegulationConfig,
  RegulationOutput,
  RegulationTelemetry,
  ChangeSurface,
  ChangeDepth,
  InvariantSurface,
  ChangeImpactInput,
  ChangeImpactResult,
  InvariantTouchResult,
  AppliedChangeRecord,
  ChangeOutcomeResult,
  ChangeOutcomeReason,
  RollbackEvent,
  RollbackRegistrySnapshot,
  RollbackConfig,
  OperatorId,
  OperatorProfile,
  OperatorValues,
  OperatorRiskPosture,
  OperatorTrustAxes,
  OperatorTrustState,
  OperatorObservation,
  OperatorTrustConfig,
  OperatorTrustPosture,
  PostureConfig,
  OperatorTrustUpdateResult,
  HighRiskDecisionLogEntry,
  ComfortPosture,
  ComfortLayerView,
  ConstitutionalFreezeState,
  ContinuitySeal,
  OperatorTrustCockpitSnapshot,
} from "./types";

export type { IntentInput, IntentMetrics } from "./intent";
export type { IdentitySnapshot } from "./identity";

export { DEFAULT_KERNEL_CONFIG, DEFAULT_KERNEL_POSTURE, DEFAULT_ALIGNMENT_CONFIG, DEFAULT_APPROVAL_GATE_CONFIG, DEFAULT_REGULATION_CONFIG, DEFAULT_ROLLBACK_CONFIG, DEFAULT_OPERATOR_TRUST_CONFIG, DEFAULT_POSTURE_CONFIG, INITIAL_OPERATOR_TRUST_STATE, HIGH_RISK_ACTIONS, DEFAULT_ALIGNMENT_POLICY } from "./types";
