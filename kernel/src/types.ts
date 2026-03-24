/**
 * Daedalus Kernel types — local type definitions for kernel-specific
 * behavior, extending the shared contracts.
 */

import type {
  AlignmentBreakdown,
  StrategyName as SharedStrategyName,
  StrategyEvaluation as SharedStrategyEvaluation,
  AlignmentContext,
} from "../../shared/daedalus/strategyAlignment";

export interface KernelConfig {
  kernelId: string;
  orchestratorUrl: string;
}

export interface BeingDescriptor {
  id: string;
  name: string;
  traits: Record<string, unknown>;
  createdAt: string;
}

// ── Strategy Names (extended with gated + escalation strategies) ──────

export type GatedStrategyName =
  | "alignment_guard_critical"
  | "alignment_guard_cautious"
  | "autonomy_paused_alignment_critical";

export type StrategyName = SharedStrategyName | GatedStrategyName;

export interface StrategyEvaluation extends Omit<SharedStrategyEvaluation, "name"> {
  name: StrategyName;
  gated?: boolean;
  originalStrategy?: SharedStrategyName;
  escalationLevel?: EscalationLevel;
}

// ── Escalation ────────────────────────────────────────────────────────

export type EscalationLevel = "none" | "medium" | "high" | "critical";

export interface EscalationResult {
  level: EscalationLevel;
  reason?: string;
}

// ── Strategy Telemetry ────────────────────────────────────────────────

export type AlignmentEventKind = "floor_breached" | "low" | "stable";

export interface AlignmentEvent {
  type: string;
  timestamp: number;
  strategy?: StrategyName;
  alignment?: number;
  [key: string]: unknown;
}

export interface StrategyTelemetryEntry {
  type: "strategy_evaluated";
  timestamp: number;
  strategy: StrategyName;
  confidence: number;
  alignment: number;
  breakdown: AlignmentBreakdown;
  gated?: boolean;
  escalationLevel?: EscalationLevel;
}

export interface AlignmentHistoryPoint {
  timestamp: number;
  strategy: StrategyName;
  alignment: number;
  confidence: number;
}

export interface AlignmentDriftResult {
  drifting: boolean;
  delta: number;
  window: number;
  firstAlignment: number | null;
  lastAlignment: number | null;
}

// ── Safe Mode ─────────────────────────────────────────────────────────

export interface SafeModeState {
  active: boolean;
  reason?: string;
  since?: number;
}

// ── Telemetry Snapshot ────────────────────────────────────────────────

export interface KernelTelemetrySnapshot {
  events: StrategyTelemetryEntry[];
  alignmentEvents: AlignmentEvent[];
  recentStrategies: StrategyEvaluation[];
  alignment: Array<{
    strategy: StrategyName;
    alignment: number;
    confidence: number;
  }>;
  alignmentHistory: AlignmentHistoryPoint[];
  drift: AlignmentDriftResult;
  lastEscalation: { level: EscalationLevel; reason?: string; strategy?: StrategyName; alignment?: number } | null;
  safeMode: SafeModeState;
  recentApprovals: ApprovalDecision[];
  lastRegulation: RegulationOutput | null;
  rollbackRegistry: RollbackRegistrySnapshot;
  operatorTrust: OperatorTrustCockpitSnapshot;
}

// ── Kernel Runtime Config ─────────────────────────────────────────────

export interface KernelRuntimeConfig {
  strategySensitivity: number;
  governanceStrictness: number;
  alignmentFloor: number;
}

export const DEFAULT_KERNEL_CONFIG: Readonly<KernelRuntimeConfig> = Object.freeze({
  strategySensitivity: 1.0,
  governanceStrictness: 0.8,
  alignmentFloor: 60,
});

// ── Alignment Config (operator-controlled) ────────────────────────────

export interface AlignmentConfig {
  sovereigntyWeight: number;
  identityWeight: number;
  governanceWeight: number;
  stabilityWeight: number;
  alignmentFloor: number;
}

export const DEFAULT_ALIGNMENT_CONFIG: Readonly<AlignmentConfig> = Object.freeze({
  sovereigntyWeight: 0.4,
  identityWeight: 0.2,
  governanceWeight: 0.3,
  stabilityWeight: 0.1,
  alignmentFloor: 60,
});

// ── Alignment Trend ───────────────────────────────────────────────────

export interface AlignmentTrend {
  avgAlignment: number | null;
  belowFloor: boolean;
  sampleCount: number;
}

// ── Kernel Posture ────────────────────────────────────────────────────

export interface KernelPosture {
  responsiveness: number;
  caution: number;
}

export const DEFAULT_KERNEL_POSTURE: Readonly<KernelPosture> = Object.freeze({
  responsiveness: 0.7,
  caution: 0.5,
});

// ── Intent ────────────────────────────────────────────────────────────

export interface IntentInterpretation {
  action: string;
  target: string | null;
  strictness: number;
  requireExplicit: boolean;
  allowShorthand: boolean;
  confidence: number;
  raw: string;
}

// ── Auto-Approval Gate ────────────────────────────────────────────────

export type ChangeProposalKind =
  | "alignment_config"
  | "kernel_config"
  | "strategy_override"
  | "posture_override"
  | "safe_mode_toggle"
  | "governance_override";

export type ChangeImpact = "low" | "medium" | "high";

export interface ChangeProposal {
  id: string;
  kind: ChangeProposalKind;
  description: string;
  payload: Record<string, unknown>;
  proposedAt: number;
  proposedBy?: string;
}

export interface ApprovalReasonBreakdown {
  alignmentOK: boolean;
  confidenceOK: boolean;
  impactOK: boolean;
  invariantsOK: boolean;
  reversibleOK: boolean;
  safeModeOK: boolean;
  cooldownOK: boolean;
}

export interface ApprovalDecision {
  autoApprove: boolean;
  proposal: ChangeProposal;
  reasons: ApprovalReasonBreakdown;
  derivedImpact: ChangeImpact;
  touchesInvariants: boolean;
  reversible: boolean;
  alignment: number;
  confidence: number;
  decidedAt: number;
}

export interface ApprovalGateConfig {
  alignmentThreshold: number;
  confidenceThreshold: number;
  cooldownMs: number;
  allowDuringSafeMode: boolean;
}

export const DEFAULT_APPROVAL_GATE_CONFIG: Readonly<ApprovalGateConfig> = Object.freeze({
  alignmentThreshold: 95,
  confidenceThreshold: 80,
  cooldownMs: 5000,
  allowDuringSafeMode: false,
});

// ── Change Classifier ─────────────────────────────────────────────────

export type ChangeSurface =
  | "telemetry"
  | "logging"
  | "ui_presentation"
  | "non_critical_config"
  | "performance_tuning"
  | "alignment_tuning"
  | "governance_policy"
  | "identity"
  | "continuity"
  | "posture"
  | "node_authority"
  | "persistence"
  | "network_topology";

export type ChangeDepth = "shallow" | "moderate" | "deep";

export type InvariantSurface =
  | "governance_policy"
  | "identity"
  | "continuity"
  | "posture"
  | "node_authority"
  | "alignment_core"
  | "safety_constraints";

export interface ChangeImpactInput {
  surfaces: ChangeSurface[];
  depth: ChangeDepth;
  reversible: boolean;
}

export interface ChangeImpactResult {
  impact: ChangeImpact;
  score: number;
  reasons: string[];
}

export interface InvariantTouchResult {
  touchesInvariants: boolean;
  invariantsTouched: InvariantSurface[];
}

// ── Rollback Registry ─────────────────────────────────────────────────

export interface AppliedChangeRecord {
  id: string;
  description: string;
  appliedAtTick: number;
  evaluationWindow: number;
  baselineAlignment: number;
  surfaces: ChangeSurface[];
  impact: ChangeImpact;
  rollbackPayload: Record<string, unknown>;
  status: "active" | "accepted" | "rolled_back";
}

export type ChangeOutcomeReason = "improved" | "neutral" | "degraded" | "window_not_reached";

export interface ChangeOutcomeResult {
  shouldRollback: boolean;
  reason: ChangeOutcomeReason;
  deltaAlignment: number;
  ticksElapsed: number;
}

export interface RollbackEvent {
  changeId: string;
  reason: ChangeOutcomeReason;
  deltaAlignment: number;
  rolledBackAt: number;
}

export interface RollbackRegistrySnapshot {
  activeChanges: AppliedChangeRecord[];
  recentRollbacks: RollbackEvent[];
  acceptedCount: number;
  rolledBackCount: number;
}

export interface RollbackConfig {
  degradationThreshold: number;
  defaultEvaluationWindow: number;
  maxActiveChanges: number;
  maxRollbackHistory: number;
}

export const DEFAULT_ROLLBACK_CONFIG: Readonly<RollbackConfig> = Object.freeze({
  degradationThreshold: 7,
  defaultEvaluationWindow: 100,
  maxActiveChanges: 20,
  maxRollbackHistory: 50,
});

// ── Alignment Regulation Loop ─────────────────────────────────────────

export interface DriftMetrics {
  magnitude: number;
  slope: number;
  acceleration: number;
}

export interface RegulationConfig {
  targetAlignment: number;
  floorAlignment: number;
  microGain: number;
  macroGain: number;
  macroDamping: number;
  macroDriftThreshold: number;
  macroAccelerationThreshold: number;
  criticalAlignmentThreshold: number;
  catastrophicAlignmentThreshold: number;
}

export const DEFAULT_REGULATION_CONFIG: Readonly<RegulationConfig> = Object.freeze({
  targetAlignment: 92,
  floorAlignment: 70,
  microGain: 0.08,
  macroGain: 0.5,
  macroDamping: 0.7,
  macroDriftThreshold: 18,
  macroAccelerationThreshold: 0.6,
  criticalAlignmentThreshold: 40,
  catastrophicAlignmentThreshold: 15,
});

export interface RegulationTelemetry {
  appliedMicro: boolean;
  appliedMacro: boolean;
  macroRawCorrection: number;
  macroDampedCorrection: number;
  reason: string;
}

export interface RegulationOutput {
  microAdjustment: number;
  macroAdjustment: number;
  shouldEnterSafeMode: boolean;
  shouldExitSafeMode: boolean;
  shouldPauseAutonomy: boolean;
  shouldResumeAutonomy: boolean;
  driftMetrics: DriftMetrics;
  telemetry: RegulationTelemetry;
}

// ── Operator Identity ─────────────────────────────────────────────────

export type OperatorId = string;

export interface OperatorValues {
  operatorSovereignty: boolean;
  noSilentRepoShifts: boolean;
  explicitNotification: boolean;
  constitutionalGovernance: boolean;
  longHorizonStability: boolean;
}

export interface OperatorRiskPosture {
  allowExperimentalNodes: boolean;
  allowAutoApproval: boolean;
  preferSafetyOverConvenience: boolean;
}

export interface OperatorProfile {
  id: OperatorId;
  displayName: string;
  values: OperatorValues;
  continuityAnchors: string[];
  risk: OperatorRiskPosture;
}

export interface OperatorTrustAxes {
  credentials: number;
  deviceGraph: number;
  behaviorProfile: number;
  continuity: number;
}

export interface OperatorTrustState {
  boundOperator: OperatorProfile | null;
  trustScore: number;
  axes: OperatorTrustAxes;
  calibrated: boolean;
  lastUpdateTick: number;
}

export interface OperatorObservation {
  tick: number;
  signals: {
    credentialsValid: boolean;
    deviceKnown: boolean;
    deviceSuspicious: boolean;
    behaviorMatchScore: number;
    continuityMatchScore: number;
    highRiskRequest: boolean;
  };
  explicitlyConfirmedCanonical?: boolean;
}

export interface OperatorTrustConfig {
  riseRate: number;
  fallRate: number;
  calibrationThreshold: number;
  highRiskTrustThreshold: number;
  weights: {
    credentials: number;
    deviceGraph: number;
    behaviorProfile: number;
    continuity: number;
  };
}

export const DEFAULT_OPERATOR_TRUST_CONFIG: Readonly<OperatorTrustConfig> = Object.freeze({
  riseRate: 1.0,
  fallRate: 5.0,
  calibrationThreshold: 75,
  highRiskTrustThreshold: 85,
  weights: Object.freeze({
    credentials: 3,
    deviceGraph: 2,
    behaviorProfile: 3,
    continuity: 2,
  }),
});

export type OperatorTrustPosture =
  | "unbound"
  | "trusted_canonical"
  | "trusted_uncalibrated"
  | "cautious"
  | "hostile_or_unknown";

export interface PostureConfig {
  trustedCanonicalThreshold: number;
  trustedUncalibratedThreshold: number;
}

export const DEFAULT_POSTURE_CONFIG: Readonly<PostureConfig> = Object.freeze({
  trustedCanonicalThreshold: 90,
  trustedUncalibratedThreshold: 70,
});

export interface OperatorTrustUpdateResult {
  state: OperatorTrustState;
  allowHighRiskActions: boolean;
  suspicious: boolean;
}

export interface HighRiskDecisionLogEntry {
  tick: number;
  action: string;
  allowed: boolean;
  posture: OperatorTrustPosture;
  trustScore: number;
  axes: OperatorTrustAxes;
  reasons: string[];
}

export type ComfortPosture = "fluid" | "neutral" | "careful";

export interface ComfortLayerView {
  posture: OperatorTrustPosture;
  comfortPosture: ComfortPosture;
  trustScore: number;
  axes: OperatorTrustAxes;
  calibrated: boolean;
  narrative: string;
  boundOperatorId: string | null;
  boundOperatorName: string | null;
}

export interface ConstitutionalFreezeState {
  frozen: boolean;
  reason: string | null;
}

export interface ContinuitySeal {
  checksum: string;
}

export interface OperatorTrustCockpitSnapshot {
  boundOperatorId: string | null;
  boundOperatorName: string | null;
  posture: OperatorTrustPosture;
  comfortPosture: ComfortPosture;
  trustScore: number;
  axes: OperatorTrustAxes;
  calibrated: boolean;
  narrative: string;
  freeze: ConstitutionalFreezeState;
  recentHighRiskDecisions: HighRiskDecisionLogEntry[];
}

export const INITIAL_OPERATOR_TRUST_STATE: Readonly<OperatorTrustState> = Object.freeze({
  boundOperator: null,
  trustScore: 0,
  axes: Object.freeze({ credentials: 0, deviceGraph: 0, behaviorProfile: 0, continuity: 0 }),
  calibrated: false,
  lastUpdateTick: 0,
});

export const HIGH_RISK_ACTIONS: readonly string[] = Object.freeze([
  "edit_governance_policy",
  "change_alignment_physiology",
  "modify_invariants",
  "node_authority_change",
  "operator_handoff",
  "safe_mode_toggle",
  "constitutional_freeze_toggle",
  "cluster_config_change",
]);

// ── Tick Result ───────────────────────────────────────────────────────

export interface KernelTickResult {
  strategy: StrategyEvaluation;
  posture: KernelPosture;
  config: KernelRuntimeConfig;
  drift: AlignmentDriftResult;
  trend: AlignmentTrend;
  selfCorrected: boolean;
  escalation: EscalationResult;
  safeMode: SafeModeState;
  intent: IntentInterpretation | null;
  approvals: ApprovalDecision[];
  regulation: RegulationOutput;
  rollbacks: RollbackEvent[];
  operatorTrust: OperatorTrustCockpitSnapshot;
}

export type {
  AlignmentBreakdown,
  AlignmentContext,
};

export type { SharedStrategyName, SharedStrategyEvaluation };
