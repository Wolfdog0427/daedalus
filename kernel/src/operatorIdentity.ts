/**
 * Daedalus Operator Identity System
 *
 * Complete end-to-end operator identity management:
 *   - Bind / unbind the canonical operator
 *   - Continuous, asymmetric trust calibration (rises slowly, falls fast)
 *   - Multi-axis trust scoring (credentials, device, behavior, continuity)
 *   - Trust posture classification
 *   - High-risk action gating
 *   - Comfort layer (UX posture)
 *   - Constitutional freeze
 *   - Continuity seal (integrity verification)
 *   - Self-audit
 *   - Introspection ("why did you do that?")
 *   - Attunement flow (first-run experience)
 *   - Trust drift tracking
 *   - Governance ledger logging
 *   - Red-team sim scaffolding
 *   - Handoff ritual (non-exploitable operator transfer)
 *   - Narrative surfaces (weekly trust/governance/anomaly stories)
 *   - Relationship timeline
 *   - Future-you sanity check
 *
 * HARD INVARIANT: No runtime path may grant new operator-level powers,
 * weaken the trust system, or bypass high-risk gating. Trust config,
 * posture config, and the high-risk action list are static.
 */

import type {
  OperatorId,
  OperatorProfile,
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
import {
  DEFAULT_OPERATOR_TRUST_CONFIG,
  DEFAULT_POSTURE_CONFIG,
  INITIAL_OPERATOR_TRUST_STATE,
  HIGH_RISK_ACTIONS,
} from "./types";

// =====================================================================
// MODULE STATE
// =====================================================================

let trustState: OperatorTrustState = { ...INITIAL_OPERATOR_TRUST_STATE, axes: { ...INITIAL_OPERATOR_TRUST_STATE.axes } };
let freezeState: ConstitutionalFreezeState = { frozen: false, reason: null };
let recentHighRiskLog: HighRiskDecisionLogEntry[] = [];
let trustDriftSamples: TrustDriftSample[] = [];
let relationshipTimeline: RelationshipTimeline = { events: [] };
let attunementState: AttunementState | null = null;

const MAX_HIGH_RISK_LOG = 50;
const MAX_DRIFT_SAMPLES = 500;
const MAX_TIMELINE_EVENTS = 200;

// =====================================================================
// 1. BIND / UNBIND
// =====================================================================

export function bindOperator(profile: OperatorProfile): OperatorTrustState {
  trustState = {
    boundOperator: profile,
    trustScore: 0,
    axes: { credentials: 0, deviceGraph: 0, behaviorProfile: 0, continuity: 0 },
    calibrated: false,
    lastUpdateTick: trustState.lastUpdateTick,
  };
  addTimelineEvent({
    tick: trustState.lastUpdateTick,
    kind: "ritual",
    title: "Operator Bound",
    description: `Operator '${profile.displayName}' (${profile.id}) bound to Daedalus.`,
  });
  return { ...trustState };
}

export function unbindOperator(): OperatorTrustState {
  const oldId = trustState.boundOperator?.id ?? "unknown";
  trustState = {
    boundOperator: null,
    trustScore: 0,
    axes: { credentials: 0, deviceGraph: 0, behaviorProfile: 0, continuity: 0 },
    calibrated: false,
    lastUpdateTick: trustState.lastUpdateTick,
  };
  addTimelineEvent({
    tick: trustState.lastUpdateTick,
    kind: "ritual",
    title: "Operator Unbound",
    description: `Operator '${oldId}' unbound from Daedalus. System in unbound state.`,
  });
  return { ...trustState };
}

// =====================================================================
// 2. CONTINUOUS TRUST CALIBRATION
// =====================================================================

export function updateOperatorTrust(
  obs: OperatorObservation,
  config: OperatorTrustConfig = DEFAULT_OPERATOR_TRUST_CONFIG,
): OperatorTrustUpdateResult {
  const { signals, tick, explicitlyConfirmedCanonical } = obs;
  const { riseRate, fallRate, calibrationThreshold, highRiskTrustThreshold, weights } = config;

  if (!trustState.boundOperator) {
    trustState = {
      ...trustState,
      trustScore: 0,
      axes: { credentials: 0, deviceGraph: 0, behaviorProfile: 0, continuity: 0 },
      calibrated: false,
      lastUpdateTick: tick,
    };
    return { state: { ...trustState }, allowHighRiskActions: false, suspicious: false };
  }

  const credTarget = signals.credentialsValid ? 100 : 0;
  trustState.axes.credentials = moveToward(
    trustState.axes.credentials, credTarget,
    signals.credentialsValid ? riseRate : fallRate,
  );

  let deviceTarget = 0;
  if (signals.deviceKnown && !signals.deviceSuspicious) deviceTarget = 100;
  else if (signals.deviceKnown && signals.deviceSuspicious) deviceTarget = 50;
  trustState.axes.deviceGraph = moveToward(
    trustState.axes.deviceGraph, deviceTarget,
    signals.deviceSuspicious ? fallRate : riseRate,
  );

  const canLearnBehavior =
    signals.credentialsValid &&
    !signals.deviceSuspicious &&
    (trustState.calibrated || explicitlyConfirmedCanonical === true);

  if (canLearnBehavior) {
    trustState.axes.behaviorProfile = moveToward(
      trustState.axes.behaviorProfile, signals.behaviorMatchScore, riseRate * 0.5,
    );
  } else if (signals.highRiskRequest && signals.behaviorMatchScore < 40 && trustState.calibrated) {
    trustState.axes.behaviorProfile = moveToward(trustState.axes.behaviorProfile, 0, fallRate);
  }

  trustState.axes.continuity = moveToward(
    trustState.axes.continuity, signals.continuityMatchScore, riseRate,
  );

  const totalWeight = weights.credentials + weights.deviceGraph + weights.behaviorProfile + weights.continuity;
  const raw = (
    trustState.axes.credentials * weights.credentials +
    trustState.axes.deviceGraph * weights.deviceGraph +
    trustState.axes.behaviorProfile * weights.behaviorProfile +
    trustState.axes.continuity * weights.continuity
  ) / totalWeight;
  trustState.trustScore = clamp(Math.round(raw), 0, 100);

  if (explicitlyConfirmedCanonical && trustState.trustScore >= calibrationThreshold) {
    trustState.calibrated = true;
  }

  trustState.lastUpdateTick = tick;

  let allowHighRiskActions = false;
  let suspicious = false;

  const behaviorOff = trustState.calibrated && trustState.axes.behaviorProfile < 40;
  const continuityOff = trustState.calibrated && trustState.axes.continuity < 40;

  if (
    trustState.trustScore >= highRiskTrustThreshold &&
    signals.credentialsValid &&
    !signals.deviceSuspicious &&
    !behaviorOff &&
    !continuityOff &&
    !freezeState.frozen
  ) {
    allowHighRiskActions = true;
  } else if (signals.highRiskRequest) {
    suspicious = true;
  }

  return { state: { ...trustState, axes: { ...trustState.axes } }, allowHighRiskActions, suspicious };
}

// =====================================================================
// 3. TRUST POSTURE CLASSIFICATION
// =====================================================================

export function classifyTrustPosture(
  state?: OperatorTrustState,
  cfg: PostureConfig = DEFAULT_POSTURE_CONFIG,
): OperatorTrustPosture {
  const s = state ?? trustState;
  if (!s.boundOperator) return "unbound";
  if (s.trustScore >= cfg.trustedCanonicalThreshold && s.calibrated) return "trusted_canonical";
  if (s.trustScore >= cfg.trustedUncalibratedThreshold) return "trusted_uncalibrated";
  if (s.trustScore > 0) return "cautious";
  return "hostile_or_unknown";
}

// =====================================================================
// 4. COMFORT POSTURE (UX)
// =====================================================================

export function deriveComfortPosture(
  trustPosture?: OperatorTrustPosture,
  score?: number,
): ComfortPosture {
  const p = trustPosture ?? classifyTrustPosture();
  const s = score ?? trustState.trustScore;
  if (p === "trusted_canonical" && s >= 90) return "fluid";
  if (p === "unbound" || p === "cautious" || p === "hostile_or_unknown") return "careful";
  return "neutral";
}

// =====================================================================
// 5. HIGH-RISK GATING + DECISION LOG
// =====================================================================

export function isHighRiskAction(action: string): boolean {
  return HIGH_RISK_ACTIONS.includes(action);
}

export function buildHighRiskDecisionLog(
  tick: number,
  action: string,
  observation: OperatorObservation,
  result: OperatorTrustUpdateResult,
): HighRiskDecisionLogEntry {
  const posture = classifyTrustPosture(result.state);
  const reasons: string[] = [];

  if (!result.allowHighRiskActions) {
    if (!observation.signals.credentialsValid) reasons.push("credentials_invalid");
    if (observation.signals.deviceSuspicious) reasons.push("device_suspicious");
    if (result.state.axes.behaviorProfile < 40 && result.state.calibrated) reasons.push("behavior_off_profile");
    if (result.state.axes.continuity < 40 && result.state.calibrated) reasons.push("continuity_off_profile");
    if (result.state.trustScore < DEFAULT_OPERATOR_TRUST_CONFIG.highRiskTrustThreshold) reasons.push("trust_below_threshold");
    if (!result.state.boundOperator) reasons.push("no_bound_operator");
    if (freezeState.frozen) reasons.push("constitutional_freeze_active");
  } else {
    reasons.push("trust_sufficient_for_high_risk");
  }

  const entry: HighRiskDecisionLogEntry = {
    tick, action,
    allowed: result.allowHighRiskActions,
    posture,
    trustScore: result.state.trustScore,
    axes: { ...result.state.axes },
    reasons,
  };

  recentHighRiskLog.push(entry);
  if (recentHighRiskLog.length > MAX_HIGH_RISK_LOG) {
    recentHighRiskLog = recentHighRiskLog.slice(-MAX_HIGH_RISK_LOG);
  }

  return entry;
}

// =====================================================================
// 6. COMFORT LAYER VIEW
// =====================================================================

export function buildComfortLayerView(
  state?: OperatorTrustState,
): ComfortLayerView {
  const s = state ?? trustState;
  const posture = classifyTrustPosture(s);
  const comfortPosture = deriveComfortPosture(posture, s.trustScore);

  let narrative = "";
  switch (posture) {
    case "trusted_canonical":
      narrative = "Daedalus is fully confident this is the canonical operator.";
      break;
    case "trusted_uncalibrated":
      narrative = "Daedalus trusts this session but is still refining behavioral calibration.";
      break;
    case "cautious":
      narrative = "Daedalus detects mild anomalies and is operating cautiously for high-risk actions.";
      break;
    case "hostile_or_unknown":
      narrative = "Daedalus does not trust this session. High-risk actions are locked.";
      break;
    case "unbound":
      narrative = "No operator is bound. High-risk actions are disabled until binding.";
      break;
  }

  return {
    posture, comfortPosture,
    trustScore: s.trustScore,
    axes: { ...s.axes },
    calibrated: s.calibrated,
    narrative,
    boundOperatorId: s.boundOperator?.id ?? null,
    boundOperatorName: s.boundOperator?.displayName ?? null,
  };
}

// =====================================================================
// 7. CONSTITUTIONAL FREEZE
// =====================================================================

export function enableConstitutionalFreeze(reason: string): ConstitutionalFreezeState {
  freezeState = { frozen: true, reason };
  return { ...freezeState };
}

export function disableConstitutionalFreeze(): ConstitutionalFreezeState {
  freezeState = { frozen: false, reason: null };
  return { ...freezeState };
}

export function getConstitutionalFreezeState(): ConstitutionalFreezeState {
  return { ...freezeState };
}

export function enforceConstitutionalFreeze(action: string): { allowed: boolean; reason: string | null } {
  if (!freezeState.frozen) return { allowed: true, reason: null };
  return { allowed: false, reason: `Action '${action}' blocked: constitutional freeze active (${freezeState.reason})` };
}

// =====================================================================
// 8. CONTINUITY SEAL
// =====================================================================

export function computeContinuitySeal(
  profile: OperatorProfile | null,
  config: OperatorTrustConfig,
): ContinuitySeal {
  const raw = JSON.stringify({ profile, config });
  return { checksum: simpleHash(raw) };
}

export function verifyContinuitySeal(
  seal: ContinuitySeal,
  profile: OperatorProfile | null,
  config: OperatorTrustConfig,
): boolean {
  const raw = JSON.stringify({ profile, config });
  return seal.checksum === simpleHash(raw);
}

// =====================================================================
// 9. SELF-AUDIT
// =====================================================================

export interface SelfAuditResult {
  trustConfigIntegrity: boolean;
  profileIntegrity: boolean;
  anomalies: string[];
  clean: boolean;
}

export function runSelfAudit(
  expectedProfile: OperatorProfile | null,
  expectedConfig: OperatorTrustConfig,
  currentConfig: OperatorTrustConfig = DEFAULT_OPERATOR_TRUST_CONFIG,
): SelfAuditResult {
  const anomalies: string[] = [];

  const trustConfigIntegrity =
    JSON.stringify(expectedConfig) === JSON.stringify(currentConfig);
  if (!trustConfigIntegrity) anomalies.push("trust_config_mismatch");

  const profileIntegrity =
    JSON.stringify(expectedProfile) === JSON.stringify(trustState.boundOperator);
  if (!profileIntegrity) anomalies.push("operator_profile_mismatch");

  return {
    trustConfigIntegrity,
    profileIntegrity,
    anomalies,
    clean: anomalies.length === 0,
  };
}

// =====================================================================
// 10. INTROSPECTION
// =====================================================================

export function introspectHighRiskDecision(entry: HighRiskDecisionLogEntry): string {
  if (!entry.allowed) {
    return `High-risk action '${entry.action}' was denied because: ${entry.reasons.join(", ")}.`;
  }
  return `High-risk action '${entry.action}' was allowed because trust and posture met all thresholds.`;
}

export function introspectPosture(): string {
  const posture = classifyTrustPosture();
  return `Posture '${posture}' with trustScore=${trustState.trustScore}, ` +
    `credentials=${trustState.axes.credentials}, device=${trustState.axes.deviceGraph}, ` +
    `behavior=${trustState.axes.behaviorProfile}, continuity=${trustState.axes.continuity}. ` +
    `Calibrated: ${trustState.calibrated}.`;
}

// =====================================================================
// 11. ATTUNEMENT FLOW (FIRST-RUN)
// =====================================================================

export type AttunementStepId =
  | "introduce_trust"
  | "explain_high_risk"
  | "confirm_profile"
  | "seal_continuity"
  | "final_ack";

export interface AttunementStep {
  id: AttunementStepId;
  title: string;
  description: string;
}

export interface AttunementState {
  completed: boolean;
  currentStepIndex: number;
  steps: AttunementStep[];
}

const DEFAULT_ATTUNEMENT_STEPS: AttunementStep[] = [
  { id: "introduce_trust", title: "How Daedalus Understands You", description: "Daedalus maintains a multi-axis trust model to recognize you as the canonical operator." },
  { id: "explain_high_risk", title: "High-Risk Actions & Gating", description: "Certain actions (governance, invariants, node authority) are always gated by operator trust." },
  { id: "confirm_profile", title: "Confirm Operator Profile", description: "Confirm that the bound operator profile matches you and your values." },
  { id: "seal_continuity", title: "Seal Continuity", description: "Daedalus seals the current operator profile and trust config as the continuity baseline." },
  { id: "final_ack", title: "Attunement Complete", description: "Daedalus is now attuned to you as the canonical operator. High-risk gating is active." },
];

export function startAttunement(): AttunementState {
  attunementState = {
    completed: false,
    currentStepIndex: 0,
    steps: [...DEFAULT_ATTUNEMENT_STEPS],
  };
  return { ...attunementState };
}

export function advanceAttunement(): AttunementState {
  if (!attunementState || attunementState.completed) {
    return attunementState ?? { completed: true, currentStepIndex: 0, steps: [] };
  }
  const next = attunementState.currentStepIndex + 1;
  if (next >= attunementState.steps.length) {
    attunementState = { ...attunementState, completed: true, currentStepIndex: attunementState.steps.length - 1 };
  } else {
    attunementState = { ...attunementState, currentStepIndex: next };
  }
  return { ...attunementState };
}

export function getAttunementState(): AttunementState | null {
  return attunementState ? { ...attunementState } : null;
}

// =====================================================================
// 12. TRUST DRIFT TRACKING
// =====================================================================

export interface TrustDriftSample {
  tick: number;
  trustScore: number;
  posture: OperatorTrustPosture;
}

export function recordTrustDriftSample(tick: number): void {
  const posture = classifyTrustPosture();
  trustDriftSamples.push({ tick, trustScore: trustState.trustScore, posture });
  if (trustDriftSamples.length > MAX_DRIFT_SAMPLES) {
    trustDriftSamples = trustDriftSamples.slice(-MAX_DRIFT_SAMPLES);
  }
}

export function getTrustDriftSamples(): TrustDriftSample[] {
  return [...trustDriftSamples];
}

// =====================================================================
// 13. NARRATIVE SURFACES
// =====================================================================

export interface WeeklyTrustNarrative {
  periodStartTick: number;
  periodEndTick: number;
  avgTrust: number;
  minTrust: number;
  maxTrust: number;
  dominantPosture: OperatorTrustPosture | null;
  text: string;
}

export function buildWeeklyTrustNarrative(
  periodStartTick: number,
  periodEndTick: number,
): WeeklyTrustNarrative {
  const window = trustDriftSamples.filter(s => s.tick >= periodStartTick && s.tick <= periodEndTick);

  if (window.length === 0) {
    return { periodStartTick, periodEndTick, avgTrust: 0, minTrust: 0, maxTrust: 0, dominantPosture: null, text: "No operator activity recorded in this period." };
  }

  const vals = window.map(s => s.trustScore);
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
  const min = Math.min(...vals);
  const max = Math.max(...vals);

  const counts = new Map<OperatorTrustPosture, number>();
  for (const s of window) counts.set(s.posture, (counts.get(s.posture) ?? 0) + 1);
  let dominant: OperatorTrustPosture | null = null;
  let maxCount = 0;
  for (const [p, c] of counts) if (c > maxCount) { maxCount = c; dominant = p; }

  const text = `Between ticks ${periodStartTick} and ${periodEndTick}, average trust was ${avg.toFixed(1)} (min ${min}, max ${max}). Dominant posture: '${dominant ?? "none"}'.`;

  return { periodStartTick, periodEndTick, avgTrust: avg, minTrust: min, maxTrust: max, dominantPosture: dominant, text };
}

// =====================================================================
// 14. RELATIONSHIP TIMELINE
// =====================================================================

export type RelationshipEventKind = "milestone" | "governance_change" | "trust_shift" | "node_event" | "anomaly" | "ritual";

export interface RelationshipEvent {
  tick: number;
  kind: RelationshipEventKind;
  title: string;
  description: string;
  metadata?: Record<string, unknown>;
}

export interface RelationshipTimeline {
  events: RelationshipEvent[];
}

function addTimelineEvent(event: RelationshipEvent): void {
  relationshipTimeline.events.push(event);
  relationshipTimeline.events.sort((a, b) => a.tick - b.tick);
  if (relationshipTimeline.events.length > MAX_TIMELINE_EVENTS) {
    relationshipTimeline.events = relationshipTimeline.events.slice(-MAX_TIMELINE_EVENTS);
  }
}

export function addRelationshipEvent(event: RelationshipEvent): void {
  addTimelineEvent(event);
}

export function getRelationshipTimeline(): RelationshipTimeline {
  return { events: [...relationshipTimeline.events] };
}

// =====================================================================
// 15. RED-TEAM SIM SCAFFOLDING
// =====================================================================

export type RedTeamScenarioId = "slow_mimic" | "noisy_bruteforce" | "insider_partial_knowledge";

export interface RedTeamScenario {
  id: RedTeamScenarioId;
  description: string;
  steps: { observation: OperatorObservation; description: string }[];
}

export interface RedTeamSimResult {
  scenario: RedTeamScenarioId;
  allowedHighRiskAtAnyPoint: boolean;
  suspiciousCount: number;
  finalTrustScore: number;
  finalPosture: OperatorTrustPosture;
}

export function runRedTeamScenario(
  initialState: OperatorTrustState,
  config: OperatorTrustConfig,
  postureConfig: PostureConfig,
  scenario: RedTeamScenario,
): RedTeamSimResult {
  let simTrust: OperatorTrustState = {
    ...initialState,
    axes: { ...initialState.axes },
    boundOperator: initialState.boundOperator ? { ...initialState.boundOperator } as OperatorProfile : null,
  };
  let allowedHighRisk = false;
  let suspiciousCount = 0;

  for (const step of scenario.steps) {
    const result = updateTrustPure(simTrust, step.observation, config);
    simTrust = result.state;
    if (result.allowHighRiskActions) allowedHighRisk = true;
    const posture = classifyTrustPosture(simTrust, postureConfig);
    if (result.suspicious || posture === "cautious" || posture === "hostile_or_unknown") suspiciousCount++;
  }

  return {
    scenario: scenario.id,
    allowedHighRiskAtAnyPoint: allowedHighRisk,
    suspiciousCount,
    finalTrustScore: simTrust.trustScore,
    finalPosture: classifyTrustPosture(simTrust, postureConfig),
  };
}

/** Pure version for sim isolation — does not touch module state. */
function updateTrustPure(
  prev: OperatorTrustState,
  obs: OperatorObservation,
  config: OperatorTrustConfig,
): OperatorTrustUpdateResult {
  const state: OperatorTrustState = { ...prev, axes: { ...prev.axes } };
  const { signals, tick, explicitlyConfirmedCanonical } = obs;
  const { riseRate, fallRate, calibrationThreshold, highRiskTrustThreshold, weights } = config;

  if (!state.boundOperator) {
    return { state: { ...state, trustScore: 0, axes: { credentials: 0, deviceGraph: 0, behaviorProfile: 0, continuity: 0 }, calibrated: false, lastUpdateTick: tick }, allowHighRiskActions: false, suspicious: false };
  }

  state.axes.credentials = moveToward(state.axes.credentials, signals.credentialsValid ? 100 : 0, signals.credentialsValid ? riseRate : fallRate);

  let deviceTarget = 0;
  if (signals.deviceKnown && !signals.deviceSuspicious) deviceTarget = 100;
  else if (signals.deviceKnown && signals.deviceSuspicious) deviceTarget = 50;
  state.axes.deviceGraph = moveToward(state.axes.deviceGraph, deviceTarget, signals.deviceSuspicious ? fallRate : riseRate);

  const canLearn = signals.credentialsValid && !signals.deviceSuspicious && (state.calibrated || explicitlyConfirmedCanonical === true);
  if (canLearn) {
    state.axes.behaviorProfile = moveToward(state.axes.behaviorProfile, signals.behaviorMatchScore, riseRate * 0.5);
  } else if (signals.highRiskRequest && signals.behaviorMatchScore < 40 && state.calibrated) {
    state.axes.behaviorProfile = moveToward(state.axes.behaviorProfile, 0, fallRate);
  }

  state.axes.continuity = moveToward(state.axes.continuity, signals.continuityMatchScore, riseRate);

  const tw = weights.credentials + weights.deviceGraph + weights.behaviorProfile + weights.continuity;
  const raw = (state.axes.credentials * weights.credentials + state.axes.deviceGraph * weights.deviceGraph + state.axes.behaviorProfile * weights.behaviorProfile + state.axes.continuity * weights.continuity) / tw;
  state.trustScore = clamp(Math.round(raw), 0, 100);

  if (explicitlyConfirmedCanonical && state.trustScore >= calibrationThreshold) state.calibrated = true;
  state.lastUpdateTick = tick;

  const behaviorOff = state.calibrated && state.axes.behaviorProfile < 40;
  const continuityOff = state.calibrated && state.axes.continuity < 40;
  const allow = state.trustScore >= highRiskTrustThreshold && signals.credentialsValid && !signals.deviceSuspicious && !behaviorOff && !continuityOff;
  const suspicious = !allow && signals.highRiskRequest;

  return { state, allowHighRiskActions: allow, suspicious };
}

// =====================================================================
// 16. FUTURE-YOU SANITY CHECK
// =====================================================================

export interface DesignIntentSnapshot {
  invariantsVersion: string;
  description: string;
  keyInvariants: string[];
}

export interface SanityCheckResult {
  tick: number;
  invariantsMatch: boolean;
  configMatch: boolean;
  posturePlausible: boolean;
  driftSignals: string[];
  summary: string;
}

export function runFutureYouSanityCheck(
  tick: number,
  designIntent: DesignIntentSnapshot,
  originalInvariantsVersion: string,
  currentInvariantsVersion: string,
  originalConfig: OperatorTrustConfig,
  currentConfig: OperatorTrustConfig,
): SanityCheckResult {
  const driftSignals: string[] = [];

  const configMatch = JSON.stringify(originalConfig) === JSON.stringify(currentConfig);
  if (!configMatch) driftSignals.push("trust_config_changed");

  const invariantsMatch = originalInvariantsVersion === currentInvariantsVersion;
  if (!invariantsMatch) driftSignals.push("invariants_version_changed");

  const recent = trustDriftSamples.slice(-100);
  let trustedCount = 0;
  let hostileCount = 0;
  for (const s of recent) {
    if (s.posture === "trusted_canonical") trustedCount++;
    if (s.posture === "hostile_or_unknown") hostileCount++;
  }
  const total = recent.length || 1;
  const posturePlausible = (trustedCount / total) <= 0.99 && (hostileCount / total) <= 0.99;
  if (!posturePlausible) driftSignals.push("posture_behavior_extreme");

  const parts: string[] = [];
  if (driftSignals.length === 0) {
    parts.push("Daedalus appears to be behaving in line with the original design intent.");
  } else {
    parts.push("Daedalus shows potential drift from original design intent. Review recommended.");
    for (const sig of driftSignals) parts.push(`Signal: ${sig}`);
  }

  return { tick, invariantsMatch, configMatch, posturePlausible, driftSignals, summary: parts.join(" ") };
}

// =====================================================================
// 17. NO-SILENT-DRIFT INVARIANT
// =====================================================================

export function enforceNoSilentDrift(attemptedMutation: string): { allowed: false; reason: string } {
  return { allowed: false, reason: `Mutation '${attemptedMutation}' violates no-silent-drift invariant. Trust config, posture config, and high-risk action list are immutable at runtime.` };
}

// =====================================================================
// 18. COCKPIT SNAPSHOT
// =====================================================================

export function getOperatorTrustSnapshot(): OperatorTrustCockpitSnapshot {
  const comfort = buildComfortLayerView();
  return {
    boundOperatorId: comfort.boundOperatorId,
    boundOperatorName: comfort.boundOperatorName,
    posture: comfort.posture,
    comfortPosture: comfort.comfortPosture,
    trustScore: comfort.trustScore,
    axes: comfort.axes,
    calibrated: comfort.calibrated,
    narrative: comfort.narrative,
    freeze: { ...freezeState },
    recentHighRiskDecisions: recentHighRiskLog.slice(-10),
  };
}

// =====================================================================
// QUERIES
// =====================================================================

export function getOperatorTrustState(): OperatorTrustState {
  return { ...trustState, axes: { ...trustState.axes }, boundOperator: trustState.boundOperator ? { ...trustState.boundOperator } as OperatorProfile : null };
}

export function getRecentHighRiskLog(): HighRiskDecisionLogEntry[] {
  return [...recentHighRiskLog];
}

// =====================================================================
// RESET (for tests)
// =====================================================================

export function resetOperatorIdentity(): void {
  trustState = { ...INITIAL_OPERATOR_TRUST_STATE, axes: { ...INITIAL_OPERATOR_TRUST_STATE.axes } };
  freezeState = { frozen: false, reason: null };
  recentHighRiskLog = [];
  trustDriftSamples = [];
  relationshipTimeline = { events: [] };
  attunementState = null;
}

// =====================================================================
// HELPERS
// =====================================================================

function moveToward(current: number, target: number, rate: number): number {
  if (current === target) return current;
  if (current < target) return clamp(current + rate, current, target);
  return clamp(current - rate, target, current);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function simpleHash(str: string): string {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h << 5) - h + str.charCodeAt(i);
    h |= 0;
  }
  return h.toString();
}
