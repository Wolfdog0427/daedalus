/**
 * Being Ontology — the canonical taxonomy of all beings in Daedalus.
 *
 * A "being" is any entity with presence, influence, and continuity.
 * Beings sit above nodes — they are the souls that inhabit the
 * orchestrated body. Nodes are limbs; beings are will.
 *
 * This file is the single source of truth for what a being IS,
 * what it CAN DO, and how it RELATES to the rest of the system.
 */

import type {
  BeingRole,
  BeingPresenceDetail,
  DaedalusPosture,
  GlowState,
  PresenceMode,
  AttentionState,
  ContinuityState,
  AutopilotState,
} from "./contracts";

// ── Being Roles ──────────────────────────────────────────────────────

export const BEING_ROLES: readonly BeingRole[] = Object.freeze([
  "OPERATOR",
  "GUARDIAN",
  "SENTINEL",
]);

export interface BeingRoleDescriptor {
  readonly role: BeingRole;
  readonly label: string;
  readonly canOverride: boolean;
  readonly canVote: boolean;
  readonly defaultInfluence: number;
  readonly defaultPresenceMode: PresenceMode;
  readonly defaultPosture: DaedalusPosture;
}

export const ROLE_DESCRIPTORS: Readonly<Record<BeingRole, BeingRoleDescriptor>> = Object.freeze({
  OPERATOR: Object.freeze({
    role: "OPERATOR" as const,
    label: "Operator",
    canOverride: true,
    canVote: true,
    defaultInfluence: 0.9,
    defaultPresenceMode: "active" as const,
    defaultPosture: "companion" as const,
  }),
  GUARDIAN: Object.freeze({
    role: "GUARDIAN" as const,
    label: "Guardian",
    canOverride: false,
    canVote: true,
    defaultInfluence: 0.4,
    defaultPresenceMode: "ambient" as const,
    defaultPosture: "sentinel" as const,
  }),
  SENTINEL: Object.freeze({
    role: "SENTINEL" as const,
    label: "Sentinel",
    canOverride: false,
    canVote: true,
    defaultInfluence: 0.3,
    defaultPresenceMode: "ambient" as const,
    defaultPosture: "observer" as const,
  }),
});

// ── Being Field Semantics ────────────────────────────────────────────

export const BEING_FIELD_SEMANTICS = Object.freeze({
  id: "Unique identifier — immutable once set",
  name: "Display name — mutable by operator only",
  posture: "Expressive archetype — sentinel, companion, observer, dormant",
  glow: "Visual energy field — level + intensity [0-1]",
  attention: "Focus state — unfocused → aware → focused → locked, optional target node",
  heartbeat: "Last heartbeat timestamp (epoch ms)",
  influenceLevel: "Weight of this being in behavioral field [0-1]",
  presenceMode: "Engagement tier — idle → ambient → active → dominant",
  isSpeaking: "Currently emitting voice/command signals",
  isGuiding: "Currently in guidance mode (affects halo + motion)",
  continuity: "Streak depth + health — drives identity continuity axis",
  autopilot: "Whether this being delegates decisions (enabled + scope)",
  updatedAt: "ISO timestamp of last mutation",
});

// ── Being Influence Paths ────────────────────────────────────────────
//
// Each being influences the system through 5 channels:
//
// 1. BEHAVIORAL: influenceLevel + presenceMode + isSpeaking + isGuiding
//    → BehavioralSignal (halo, motion, guidance cue, weight)
//    → BehavioralField (dominant being, signal array)
//
// 2. EXPRESSIVE: dominant being's posture, glow, attention
//    → ExpressiveField (system-level posture, glow, attention)
//    → arousal (from behavioral intensity)
//    → focus (from dominant being weight)
//    → stability (from fraction of beings with healthy continuity)
//
// 3. CONTINUITY: continuity.streak, continuity.healthy
//    → ContinuitySignals (recency, streak, threshold, drift-recovery, anchor)
//    → SystemContinuity.identity axis (being stability + streak depth)
//    → anchorBeingId (longest streak among beings)
//
// 4. GOVERNANCE: BeingIdFull on overrides (createdBy), BeingVote on events
//    → GovernanceService posture computation (via votes)
//    → Override attribution chain
//
// 5. PRESENCE: presenceMode + attention + heartbeat
//    → Cockpit visibility (BeingPresencePanel, HUD)
//    → Embodied presence (being count, dominant being)
//    → Node attention targeting (attention.targetNodeId)

export const BEING_INFLUENCE_PATHS = Object.freeze([
  "behavioral",
  "expressive",
  "continuity",
  "governance",
  "presence",
] as const);

export type BeingInfluencePath = typeof BEING_INFLUENCE_PATHS[number];

// ── Canonical Seed Beings ────────────────────────────────────────────

function nowIso(): string {
  return new Date().toISOString();
}

export function createCanonicalOperator(): BeingPresenceDetail {
  return {
    id: "operator",
    name: "Operator",
    posture: "companion",
    glow: { level: "high", intensity: 0.85 },
    attention: { level: "focused" },
    heartbeat: Date.now(),
    influenceLevel: ROLE_DESCRIPTORS.OPERATOR.defaultInfluence,
    presenceMode: ROLE_DESCRIPTORS.OPERATOR.defaultPresenceMode,
    isSpeaking: false,
    isGuiding: true,
    continuity: { streak: 12, lastCheckIn: nowIso(), healthy: true },
    autopilot: { enabled: false, scope: "none" },
    updatedAt: nowIso(),
  };
}

export function createCanonicalGuardian(id: string, name: string): BeingPresenceDetail {
  return {
    id,
    name,
    posture: ROLE_DESCRIPTORS.GUARDIAN.defaultPosture,
    glow: { level: "medium", intensity: 0.5 },
    attention: { level: "aware" },
    heartbeat: Date.now(),
    influenceLevel: ROLE_DESCRIPTORS.GUARDIAN.defaultInfluence,
    presenceMode: ROLE_DESCRIPTORS.GUARDIAN.defaultPresenceMode,
    isSpeaking: false,
    isGuiding: false,
    continuity: { streak: 7, lastCheckIn: nowIso(), healthy: true },
    autopilot: { enabled: true, scope: "local" },
    updatedAt: nowIso(),
  };
}

export function createCanonicalSentinel(id: string, name: string): BeingPresenceDetail {
  return {
    id,
    name,
    posture: ROLE_DESCRIPTORS.SENTINEL.defaultPosture,
    glow: { level: "low", intensity: 0.3 },
    attention: { level: "aware" },
    heartbeat: Date.now(),
    influenceLevel: ROLE_DESCRIPTORS.SENTINEL.defaultInfluence,
    presenceMode: ROLE_DESCRIPTORS.SENTINEL.defaultPresenceMode,
    isSpeaking: false,
    isGuiding: false,
    continuity: { streak: 0, lastCheckIn: nowIso(), healthy: true },
    autopilot: { enabled: true, scope: "local" },
    updatedAt: nowIso(),
  };
}

// ── Being Relationships ──────────────────────────────────────────────

export const BEING_RELATIONSHIPS = Object.freeze({
  beingToNode: "A being oversees nodes via operatorId / attention.targetNodeId",
  beingToGovernance: "A being authors overrides (createdBy) and casts votes",
  beingToContinuity: "A being's streak and health feed identity continuity",
  beingToExpressive: "The dominant being sets system posture, glow, and attention",
  beingToBeing: "Multiple beings form a behavioral field; dominance = highest weight",
});

// ── Being Lifecycle States ───────────────────────────────────────────

export const BEING_PRESENCE_MODES: readonly PresenceMode[] = Object.freeze([
  "idle",
  "ambient",
  "active",
  "dominant",
]);

export const BEING_ATTENTION_LEVELS: readonly AttentionState["level"][] = Object.freeze([
  "unfocused",
  "aware",
  "focused",
  "locked",
]);

export const BEING_POSTURE_ARCHETYPES: readonly DaedalusPosture[] = Object.freeze([
  "sentinel",
  "companion",
  "observer",
  "dormant",
]);
