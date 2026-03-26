export type RiskTier = "low" | "medium" | "high";
export type GlowLevel = "none" | "low" | "medium" | "high";

export type NodeStatus = "unknown" | "pending" | "trusted" | "degraded" | "quarantined" | "detached";

export interface Capability {
  name: string;
  value: string;
  enabled: boolean;
}

export interface NodePresence {
  id: string;
  status: NodeStatus;
  lastHeartbeat: string | null;
  glow: GlowLevel;
  risk: RiskTier;
  capabilities: Capability[];
}

export interface BeingId {
  id: string;
}

export interface BeingPresence {
  id: string;
  label: string;
  nodes: string[];
  dominantGlow: GlowLevel;
  dominantRisk: RiskTier;
}

export type CapabilityReasonCode =
  | "NODE_VETO"
  | "RISK_ESCALATION"
  | "POSTURE_MISMATCH"
  | "GOVERNANCE_OVERRIDE"
  | "CONTINUITY_DRIFT"
  | "NOT_PRESENT";

export interface CapabilityTraceStep {
  level: "node" | "being" | "orchestrator" | "governance";
  sourceId: string;
  reason: CapabilityReasonCode;
  message: string;
  timestamp: string;
}

export interface CapabilityTrace {
  nodeId: string;
  capabilityName: string;
  effectiveEnabled: boolean;
  steps: CapabilityTraceStep[];
}

export interface NegotiationInput {
  requestedBy: BeingId;
  targetNodeId: string;
  capabilityName: string;
  desiredEnabled: boolean;
}

export interface NegotiationDecision {
  capabilityName: string;
  fromEnabled: boolean;
  toEnabled: boolean;
  reason: CapabilityReasonCode | null;
  message: string;
}

export interface NegotiationPreview {
  nodeId: string;
  requestedBy: BeingId;
  decisions: NegotiationDecision[];
}

export interface NegotiationApplyResult {
  nodeId: string;
  applied: boolean;
  decisions: NegotiationDecision[];
}

export interface OrchestratorSnapshot {
  nodes: NodePresence[];
  beings: BeingPresenceDetail[];
}

// ── Governance & Posture (v0.7) ──────────────────────────────────────

export type BeingRole = "OPERATOR" | "GUARDIAN" | "SENTINEL";

export interface BeingIdFull {
  id: string;
  role: BeingRole;
  label: string;
}

export type PostureState = "OPEN" | "ATTENTIVE" | "GUARDED" | "LOCKDOWN";

export interface GovernanceOverride {
  id: string;
  createdAt: string;
  createdBy: BeingIdFull;
  reason: string;
  scope: "NODE" | "CAPABILITY" | "GLOBAL";
  targetId?: string;
  effect: "ALLOW" | "DENY" | "ESCALATE";
  expiresAt?: string;
}

export interface ContinuityDrift {
  id: string;
  detectedAt: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  summary: string;
  expiresAt?: string;
}

export interface PostureSnapshot {
  posture: PostureState;
  reason: string;
  since: string;
  activeOverrides: GovernanceOverride[];
  activeDrifts: ContinuityDrift[];
}

export interface BeingVote {
  being: BeingIdFull;
  vote: "ALLOW" | "DENY" | "ESCALATE";
  weight: number;
}

// ── Being-Level Presence & Influence (v0.8) ───────────────────────────

export type DaedalusPosture = "sentinel" | "companion" | "observer" | "dormant";

export interface GlowState {
  level: GlowLevel;
  intensity: number;
}

export interface AttentionState {
  level: "unfocused" | "aware" | "focused" | "locked";
  targetNodeId?: string;
}

export interface ContinuityState {
  streak: number;
  lastCheckIn: string;
  healthy: boolean;
}

export interface AutopilotState {
  enabled: boolean;
  scope: "none" | "local" | "global";
}

export type PresenceMode = "idle" | "ambient" | "active" | "dominant";

export interface BeingPresenceDetail {
  id: string;
  name: string;

  posture: DaedalusPosture;
  glow: GlowState;
  attention: AttentionState;
  heartbeat: number;

  influenceLevel: number;
  presenceMode: PresenceMode;
  isSpeaking: boolean;
  isGuiding: boolean;

  continuity: ContinuityState;
  autopilot: AutopilotState;

  updatedAt: string;
}

export interface BeingPresenceEvent {
  type: "BEING_PRESENCE_UPDATED";
  beingId: string;
  payload: BeingPresenceDetail;
  timestamp: string;
}

// ── Behavioral Grammar Engine (v0.9) ─────────────────────────────────

export type AvatarMicroMotion = "none" | "tilt" | "lean" | "pulse";
export type GuidanceCue = "none" | "subtle" | "strong";

export interface BehavioralSignal {
  beingId: string;
  haloIntensity: number;
  haloColorShift: number;
  avatarMicroMotion: AvatarMicroMotion;
  guidanceCue: GuidanceCue;
  influenceWeight: number;
  updatedAt: number;
}

export interface BehavioralField {
  signals: BehavioralSignal[];
  dominantBeingId: string | null;
  updatedAt: number;
}

// ── Unified Expressive Field (v1.0) ──────────────────────────────────

export interface ExpressiveField {
  posture: DaedalusPosture;
  glow: GlowState;
  attention: AttentionState;
  continuity: ContinuityState;
  behavioral: BehavioralField;

  arousal: number;
  focus: number;
  stability: number;

  updatedAt: number;
}
