import type {
  OrchestratorSnapshot,
  CapabilityTrace,
  NegotiationPreview,
  NegotiationApplyResult,
  NegotiationInput,
  PostureSnapshot,
  GovernanceOverride,
  ContinuityDrift,
  BeingPresenceDetail,
} from "../shared/daedalus/contracts";

const basePath = import.meta.env.VITE_DAEDALUS_API_BASE || "/daedalus";

const TOKEN = import.meta.env.VITE_DAEDALUS_TOKEN ?? "daedalus-dev-token";

function authHeaders(): Record<string, string> {
  return { "Content-Type": "application/json", "x-daedalus-token": TOKEN };
}

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Daedalus API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function handleVoid(res: Response): Promise<void> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Daedalus API error ${res.status}: ${text}`);
  }
}

export async function fetchSnapshot(): Promise<OrchestratorSnapshot> {
  const res = await fetch(`${basePath}/snapshot`, { headers: authHeaders() });
  return handleJson<OrchestratorSnapshot>(res);
}

export async function fetchCapabilityTrace(
  nodeId: string,
  capabilityName: string,
): Promise<CapabilityTrace> {
  const params = new URLSearchParams({ nodeId, capabilityName });
  const res = await fetch(`${basePath}/capabilities/trace?${params.toString()}`, {
    headers: authHeaders(),
  });
  return handleJson<CapabilityTrace>(res);
}

export async function previewNegotiation(
  input: NegotiationInput,
): Promise<NegotiationPreview> {
  const res = await fetch(`${basePath}/negotiations/preview`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson<NegotiationPreview>(res);
}

export async function applyNegotiation(
  input: NegotiationInput,
): Promise<NegotiationApplyResult> {
  const res = await fetch(`${basePath}/negotiations/apply`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson<NegotiationApplyResult>(res);
}

export async function fetchPosture(): Promise<PostureSnapshot> {
  const res = await fetch(`${basePath}/governance/posture`, { headers: authHeaders() });
  return handleJson<PostureSnapshot>(res);
}

export async function fetchOverrides(): Promise<GovernanceOverride[]> {
  const res = await fetch(`${basePath}/governance/overrides`, { headers: authHeaders() });
  return handleJson<GovernanceOverride[]>(res);
}

export async function fetchDrifts(): Promise<ContinuityDrift[]> {
  const res = await fetch(`${basePath}/governance/drifts`, { headers: authHeaders() });
  return handleJson<ContinuityDrift[]>(res);
}

export async function fetchBeingPresences(): Promise<BeingPresenceDetail[]> {
  const res = await fetch(`${basePath}/beings/presence`, { headers: authHeaders() });
  return handleJson<BeingPresenceDetail[]>(res);
}

export async function updateBeingPresence(
  beingId: string,
  patch: Partial<BeingPresenceDetail>,
): Promise<BeingPresenceDetail> {
  const res = await fetch(`${basePath}/beings/${beingId}/presence`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(patch),
  });
  return handleJson<BeingPresenceDetail>(res);
}

// ── Strategy Alignment ────────────────────────────────────────────

export interface AlignmentBreakdown {
  sovereignty: number;
  identity: number;
  governance: number;
  stability: number;
}

export type StrategyName =
  | "sovereignty_stable"
  | "sovereignty_contested"
  | "identity_reinforcement"
  | "governance_attentive"
  | "governance_undercorrection"
  | "stability_recovery"
  | "alignment_nominal"
  | "alignment_degraded"
  | "alignment_guard_critical"
  | "alignment_guard_cautious"
  | "autonomy_paused_alignment_critical";

export type EscalationLevel = "none" | "medium" | "high" | "critical";

export interface EscalationResult {
  level: EscalationLevel;
  reason?: string;
}

export interface SafeModeState {
  active: boolean;
  reason?: string;
  since?: number;
}

export interface StrategyEvaluation {
  name: StrategyName;
  confidence: number;
  alignment: number;
  alignmentBreakdown: AlignmentBreakdown;
  weakestAxis: keyof AlignmentBreakdown;
  strongestAxis: keyof AlignmentBreakdown;
  notes: string;
  evaluatedAt: string;
  gated?: boolean;
  originalStrategy?: string;
  escalationLevel?: EscalationLevel;
}

export interface AlignmentDriftResult {
  drifting: boolean;
  delta: number;
  window: number;
  firstAlignment: number | null;
  lastAlignment: number | null;
}

export interface KernelPosture {
  responsiveness: number;
  caution: number;
}

export interface AlignmentTrend {
  avgAlignment: number | null;
  belowFloor: boolean;
  sampleCount: number;
}

export interface StrategyResponse extends StrategyEvaluation {
  posture: KernelPosture | null;
  drift: AlignmentDriftResult | null;
  selfCorrected: boolean;
  trend: AlignmentTrend | null;
  escalation: EscalationResult | null;
  safeMode: SafeModeState | null;
}

export async function fetchStrategy(): Promise<StrategyResponse> {
  const res = await fetch(`${basePath}/strategy`, { headers: authHeaders() });
  return handleJson<StrategyResponse>(res);
}

export interface AlignmentHistoryPoint {
  timestamp: number;
  strategy: StrategyName;
  alignment: number;
  confidence: number;
}

export interface TelemetrySnapshot {
  events: Array<{
    type: string;
    timestamp: number;
    strategy: StrategyName;
    confidence: number;
    alignment: number;
    breakdown: AlignmentBreakdown;
    gated?: boolean;
    escalationLevel?: EscalationLevel;
  }>;
  alignmentEvents: Array<{
    type: string;
    timestamp: number;
    strategy?: StrategyName;
    alignment?: number;
  }>;
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
}

// ── Alignment Config ──────────────────────────────────────────────

export interface AlignmentConfig {
  sovereigntyWeight: number;
  identityWeight: number;
  governanceWeight: number;
  stabilityWeight: number;
  alignmentFloor: number;
}

export async function fetchAlignmentConfig(): Promise<AlignmentConfig> {
  const res = await fetch(`${basePath}/alignment-config`, { headers: authHeaders() });
  return handleJson<AlignmentConfig>(res);
}

export async function saveAlignmentConfig(config: Partial<AlignmentConfig>): Promise<AlignmentConfig> {
  const res = await fetch(`${basePath}/alignment-config`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(config),
  });
  return handleJson<AlignmentConfig>(res);
}

// ── Auto-Approval Gate ───────────────────────────────────────────

export type ChangeProposalKind =
  | "alignment_config"
  | "kernel_config"
  | "strategy_override"
  | "posture_override"
  | "safe_mode_toggle"
  | "governance_override"
  | "governance_policy"
  | "regulation_tuning"
  | "posture_shift"
  | "node_authority"
  | "identity_update"
  | "telemetry_config"
  | "other";

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

export interface ApprovalGateResponse {
  config: ApprovalGateConfig;
  recentDecisions: ApprovalDecision[];
}

export async function fetchApprovalGate(): Promise<ApprovalGateResponse> {
  const res = await fetch(`${basePath}/approval-gate`, { headers: authHeaders() });
  return handleJson<ApprovalGateResponse>(res);
}

export async function submitChangeProposal(proposal: Partial<ChangeProposal> & { kind: ChangeProposalKind; description: string }): Promise<ApprovalDecision> {
  const res = await fetch(`${basePath}/propose-change`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(proposal),
  });
  return handleJson<ApprovalDecision>(res);
}

export async function updateApprovalGateConfig(patch: Partial<ApprovalGateConfig>): Promise<ApprovalGateConfig> {
  const res = await fetch(`${basePath}/approval-gate/config`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(patch),
  });
  return handleJson<ApprovalGateConfig>(res);
}

// ── Daedalus-Initiated Proposals ─────────────────────────────────

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

export async function fetchPendingProposals(): Promise<DaedalusProposal[]> {
  const res = await fetch(`${basePath}/proposals/pending`, { headers: authHeaders() });
  return handleJson<DaedalusProposal[]>(res);
}

export async function fetchProposalHistory(): Promise<ProposalHistoryEntry[]> {
  const res = await fetch(`${basePath}/proposals/history`, { headers: authHeaders() });
  return handleJson<ProposalHistoryEntry[]>(res);
}

export async function approveDaedalusProposal(id: string): Promise<DaedalusProposal> {
  const res = await fetch(`${basePath}/proposals/${id}/approve`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleJson<DaedalusProposal>(res);
}

export async function denyDaedalusProposal(id: string): Promise<DaedalusProposal> {
  const res = await fetch(`${basePath}/proposals/${id}/deny`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleJson<DaedalusProposal>(res);
}

export async function fetchTelemetry(): Promise<TelemetrySnapshot> {
  const res = await fetch(`${basePath}/telemetry`, { headers: authHeaders() });
  return handleJson<TelemetrySnapshot>(res);
}

// ── Alignment Regulation Loop ────────────────────────────────────

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

export interface RegulationResponse {
  config: RegulationConfig;
  lastOutput: RegulationOutput | null;
}

export async function fetchRegulation(): Promise<RegulationResponse> {
  const res = await fetch(`${basePath}/regulation`, { headers: authHeaders() });
  return handleJson<RegulationResponse>(res);
}

export async function updateRegulationConfig(patch: Partial<RegulationConfig>): Promise<RegulationConfig> {
  const res = await fetch(`${basePath}/regulation/config`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(patch),
  });
  return handleJson<RegulationConfig>(res);
}

// ── Change Classifier + Rollback Registry ────────────────────────

export type ChangeSurface =
  | "telemetry" | "logging" | "ui_presentation" | "non_critical_config"
  | "performance_tuning" | "alignment_tuning" | "governance_policy"
  | "identity" | "continuity" | "posture" | "node_authority"
  | "persistence" | "network_topology";

export type ChangeDepth = "shallow" | "moderate" | "deep";

export type InvariantSurface =
  | "governance_policy" | "identity" | "continuity" | "posture"
  | "node_authority" | "alignment_core" | "safety_constraints";

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

export interface RollbackEvent {
  changeId: string;
  reason: string;
  deltaAlignment: number;
  rolledBackAt: number;
}

export interface RollbackRegistrySnapshot {
  activeChanges: AppliedChangeRecord[];
  recentRollbacks: RollbackEvent[];
  acceptedCount: number;
  rolledBackCount: number;
}

export async function fetchRollbackRegistry(): Promise<RollbackRegistrySnapshot> {
  const res = await fetch(`${basePath}/rollback-registry`, { headers: authHeaders() });
  return handleJson<RollbackRegistrySnapshot>(res);
}

export async function classifyChangeRequest(input: {
  surfaces: ChangeSurface[];
  depth: ChangeDepth;
  reversible: boolean;
}): Promise<{
  impact: { impact: ChangeImpact; score: number; reasons: string[] };
  invariants: { touchesInvariants: boolean; invariantsTouched: InvariantSurface[] };
}> {
  const res = await fetch(`${basePath}/classify-change`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson(res);
}

// ── Operator Identity ────────────────────────────────────────────

export type OperatorTrustPosture =
  | "unbound" | "trusted_canonical" | "trusted_uncalibrated"
  | "cautious" | "hostile_or_unknown";

export type ComfortPosture = "fluid" | "neutral" | "careful";

export interface OperatorTrustAxes {
  credentials: number;
  deviceGraph: number;
  behaviorProfile: number;
  continuity: number;
}

export interface ConstitutionalFreezeState {
  frozen: boolean;
  reason: string | null;
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

export async function fetchOperatorTrust(): Promise<OperatorTrustCockpitSnapshot> {
  const res = await fetch(`${basePath}/operator/trust`, { headers: authHeaders() });
  return handleJson<OperatorTrustCockpitSnapshot>(res);
}

export async function bindOperatorProfile(profile: {
  id: string;
  displayName: string;
  values?: Record<string, boolean>;
  continuityAnchors?: string[];
  risk?: Record<string, boolean>;
}): Promise<unknown> {
  const res = await fetch(`${basePath}/operator/bind`, {
    method: "POST", headers: authHeaders(), body: JSON.stringify(profile),
  });
  return handleJson(res);
}

export async function unbindOperator(): Promise<unknown> {
  const res = await fetch(`${basePath}/operator/unbind`, {
    method: "POST", headers: authHeaders(),
  });
  return handleJson(res);
}

export async function fetchOperatorHighRiskLog(): Promise<HighRiskDecisionLogEntry[]> {
  const res = await fetch(`${basePath}/operator/high-risk-log`, { headers: authHeaders() });
  return handleJson<HighRiskDecisionLogEntry[]>(res);
}

export async function enableFreeze(reason: string): Promise<ConstitutionalFreezeState> {
  const res = await fetch(`${basePath}/operator/freeze`, {
    method: "POST", headers: authHeaders(), body: JSON.stringify({ reason }),
  });
  return handleJson<ConstitutionalFreezeState>(res);
}

export async function disableFreeze(): Promise<ConstitutionalFreezeState> {
  const res = await fetch(`${basePath}/operator/unfreeze`, {
    method: "POST", headers: authHeaders(),
  });
  return handleJson<ConstitutionalFreezeState>(res);
}

export async function fetchOperatorIntrospection(): Promise<{ explanation: string }> {
  const res = await fetch(`${basePath}/operator/introspect`, { headers: authHeaders() });
  return handleJson<{ explanation: string }>(res);
}

// ── Cockpit (sensory cortex) ──────────────────────────────────────

export interface CockpitNodeView {
  id: string;
  name: string;
  status: string;
  risk: string;
  phase: string;
  kind: string;
  glow: string;
  glowIntensity: number;
  posture: string;
  attention: { level: string; targetNodeId?: string };
  continuity: string;
  capabilities: string[];
  heartbeatCount: number;
  lastHeartbeatAt: string | null;
  errorCount: number;
}

export interface CockpitSummary {
  totalNodes: number;
  byStatus: Record<string, number>;
  byPosture: Record<string, number>;
  byRisk: Record<string, number>;
  totalErrors: number;
  posture?: string;
  postureReason?: string;
  urgency?: "calm" | "attentive" | "elevated" | "critical";
  recommendedActions?: string[];
  activeDriftCount?: number;
  activeOverrideCount?: number;
}

export interface Incident {
  id: string;
  title: string;
  notes: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: "open" | "investigating" | "mitigated" | "resolved";
  openedAt: string;
  closedAt: string | null;
  updatedAt: string;
}

export interface ActionEntry {
  id: number;
  kind: string;
  timestamp: string;
  payload: any;
  undone: boolean;
  undoable: boolean;
}

export async function fetchCockpitNodes(): Promise<CockpitNodeView[]> {
  const res = await fetch(`${basePath}/cockpit/nodes`, { headers: authHeaders() });
  return handleJson<CockpitNodeView[]>(res);
}

export async function fetchCockpitSummary(): Promise<CockpitSummary> {
  const res = await fetch(`${basePath}/cockpit/summary`, { headers: authHeaders() });
  return handleJson<CockpitSummary>(res);
}

export async function createOverride(input: {
  createdBy: { id: string; role: string; label: string };
  reason: string;
  scope: string;
  targetId?: string;
  effect: string;
}): Promise<GovernanceOverride> {
  const res = await fetch(`${basePath}/governance/overrides`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson<GovernanceOverride>(res);
}

export async function removeOverride(id: string): Promise<void> {
  const res = await fetch(`${basePath}/governance/overrides/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await handleVoid(res);
}

export async function clearOverrides(): Promise<void> {
  const res = await fetch(`${basePath}/governance/overrides`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await handleVoid(res);
}

export async function castVote(input: {
  being: { id: string; role: string; label: string };
  vote: string;
  weight: number;
}): Promise<any> {
  const res = await fetch(`${basePath}/governance/votes`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson<any>(res);
}

export async function fetchVotes(): Promise<any[]> {
  const res = await fetch(`${basePath}/governance/votes`, { headers: authHeaders() });
  return handleJson<any[]>(res);
}

export async function clearVotes(): Promise<void> {
  const res = await fetch(`${basePath}/governance/votes`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await handleVoid(res);
}

export async function clearDrifts(): Promise<void> {
  const res = await fetch(`${basePath}/governance/drifts`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await handleVoid(res);
}

export async function fetchConstitution(): Promise<any> {
  const res = await fetch(`${basePath}/constitution`, { headers: authHeaders() });
  return handleJson<any>(res);
}

// ── Event History ──────────────────────────────────────────────────

export async function fetchEventHistory(limit = 100, type?: string): Promise<any[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (type) params.set("type", type);
  const res = await fetch(`${basePath}/events/history?${params.toString()}`, { headers: authHeaders() });
  return handleJson<any[]>(res);
}

// ── Incidents ──────────────────────────────────────────────────────

export async function fetchIncidents(status?: string): Promise<Incident[]> {
  const params = status ? `?status=${status}` : "";
  const res = await fetch(`${basePath}/incidents${params}`, { headers: authHeaders() });
  return handleJson<Incident[]>(res);
}

export async function openIncident(input: { title: string; notes?: string; severity: string }): Promise<Incident> {
  const res = await fetch(`${basePath}/incidents`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  return handleJson<Incident>(res);
}

export async function updateIncident(id: string, patch: Partial<Incident>): Promise<Incident> {
  const res = await fetch(`${basePath}/incidents/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(patch),
  });
  return handleJson<Incident>(res);
}

export async function resolveIncident(id: string): Promise<Incident> {
  const res = await fetch(`${basePath}/incidents/${id}/resolve`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleJson<Incident>(res);
}

// ── Action Log & Undo ──────────────────────────────────────────────

export async function fetchActions(limit = 50): Promise<ActionEntry[]> {
  const res = await fetch(`${basePath}/actions?limit=${limit}`, { headers: authHeaders() });
  return handleJson<ActionEntry[]>(res);
}

export async function undoAction(actionId: number): Promise<{ success: boolean }> {
  const res = await fetch(`${basePath}/actions/${actionId}/undo`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleJson<{ success: boolean }>(res);
}

// ── Chat ──────────────────────────────────────────────────────────────

export type ChatRole = "operator" | "daedalus" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  userMessage: ChatMessage;
  daedalusMessage: ChatMessage;
  reply: string;
  intent: string;
  confidence: number;
  context: {
    lastIntent: string | null;
    lastTopic: string | null;
  };
}

export interface ChatHelpEntry {
  name: string;
  description: string;
  examples: string[];
}

export async function sendChatMessage(content: string, sessionId?: string): Promise<ChatResponse> {
  const res = await fetch(`${basePath}/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ message: content, sessionId }),
  });
  return handleJson<ChatResponse>(res);
}

export async function fetchChatHistory(limit = 100): Promise<ChatMessage[]> {
  const res = await fetch(`${basePath}/chat/history?limit=${limit}`, { headers: authHeaders() });
  return handleJson<ChatMessage[]>(res);
}

export async function clearChat(): Promise<void> {
  const res = await fetch(`${basePath}/chat/history`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await handleVoid(res);
}

export async function fetchChatWelcome(): Promise<ChatMessage> {
  const res = await fetch(`${basePath}/chat/welcome`, { headers: authHeaders() });
  return handleJson<ChatMessage>(res);
}

export async function fetchChatHelp(): Promise<{ intents: ChatHelpEntry[] }> {
  const res = await fetch(`${basePath}/chat/help`, { headers: authHeaders() });
  return handleJson<{ intents: ChatHelpEntry[] }>(res);
}
