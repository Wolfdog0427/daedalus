/**
 * Being Constitution — the unbreakable laws governing all beings.
 *
 * This is the final missing piece of Daedalus's law.
 * Every invariant here is either:
 * - **structural**: guaranteed by the architecture
 * - **runtime**: validated against live state
 *
 * A violation means a bug, not an operator error.
 */

import type { BeingPresenceDetail, BeingRole, DaedalusPosture, PresenceMode, BeingVote } from "./contracts";
import { BEING_ROLES, ROLE_DESCRIPTORS, BEING_POSTURE_ARCHETYPES, BEING_PRESENCE_MODES, BEING_ATTENTION_LEVELS } from "./beingOntology";

// ── Constitutional Constants ─────────────────────────────────────────

export const BEING_CONSTITUTION_VERSION = "1.0.0";

export const MAX_BEINGS = 50;
export const MAX_VOTES_PER_BEING = 1;
export const MAX_INFLUENCE_LEVEL = 1.0;
export const MIN_INFLUENCE_LEVEL = 0.0;
export const ANCHOR_STREAK_MINIMUM = 4;

// ── Invariant Types ──────────────────────────────────────────────────

export type BeingInvariantName =
  | "valid-posture"
  | "valid-presence-mode"
  | "valid-attention-level"
  | "bounded-influence"
  | "continuity-coherent"
  | "anchor-exists"
  | "single-vote-per-being"
  | "vote-weight-bounded"
  | "dominant-is-present"
  | "operator-always-present";

export interface BeingInvariantCheck {
  name: BeingInvariantName;
  passed: boolean;
  detail?: string;
}

export interface BeingInvariantReport {
  allPassed: boolean;
  checks: BeingInvariantCheck[];
  failedCount: number;
}

// ── Invariant Validators ─────────────────────────────────────────────

function checkValidPosture(beings: BeingPresenceDetail[]): BeingInvariantCheck {
  const invalid = beings.filter(b => !(BEING_POSTURE_ARCHETYPES as readonly string[]).includes(b.posture));
  return {
    name: "valid-posture",
    passed: invalid.length === 0,
    detail: invalid.length > 0 ? `Invalid postures: ${invalid.map(b => `${b.id}=${b.posture}`).join(", ")}` : undefined,
  };
}

function checkValidPresenceMode(beings: BeingPresenceDetail[]): BeingInvariantCheck {
  const invalid = beings.filter(b => !(BEING_PRESENCE_MODES as readonly string[]).includes(b.presenceMode));
  return {
    name: "valid-presence-mode",
    passed: invalid.length === 0,
    detail: invalid.length > 0 ? `Invalid modes: ${invalid.map(b => `${b.id}=${b.presenceMode}`).join(", ")}` : undefined,
  };
}

function checkValidAttentionLevel(beings: BeingPresenceDetail[]): BeingInvariantCheck {
  const invalid = beings.filter(b => !(BEING_ATTENTION_LEVELS as readonly string[]).includes(b.attention.level));
  return {
    name: "valid-attention-level",
    passed: invalid.length === 0,
    detail: invalid.length > 0 ? `Invalid levels: ${invalid.map(b => `${b.id}=${b.attention.level}`).join(", ")}` : undefined,
  };
}

function checkBoundedInfluence(beings: BeingPresenceDetail[]): BeingInvariantCheck {
  const outOfBounds = beings.filter(
    b => b.influenceLevel < MIN_INFLUENCE_LEVEL || b.influenceLevel > MAX_INFLUENCE_LEVEL,
  );
  return {
    name: "bounded-influence",
    passed: outOfBounds.length === 0,
    detail: outOfBounds.length > 0 ? `Out of bounds: ${outOfBounds.map(b => `${b.id}=${b.influenceLevel}`).join(", ")}` : undefined,
  };
}

function checkContinuityCoherent(beings: BeingPresenceDetail[]): BeingInvariantCheck {
  const incoherent = beings.filter(
    b => b.continuity.streak < 0 || (b.continuity.streak === 0 && b.continuity.healthy && beings.length === 1),
  );
  return {
    name: "continuity-coherent",
    passed: incoherent.length === 0,
    detail: incoherent.length > 0 ? `Questionable continuity: ${incoherent.map(b => b.id).join(", ")}` : undefined,
  };
}

function checkAnchorExists(beings: BeingPresenceDetail[]): BeingInvariantCheck {
  if (beings.length === 0) {
    return { name: "anchor-exists", passed: false, detail: "No beings present — no anchor possible" };
  }
  const maxStreak = Math.max(...beings.map(b => b.continuity.streak));
  return {
    name: "anchor-exists",
    passed: maxStreak >= ANCHOR_STREAK_MINIMUM || beings.length === 1,
    detail: maxStreak < ANCHOR_STREAK_MINIMUM ? `Best streak ${maxStreak} < minimum ${ANCHOR_STREAK_MINIMUM}` : undefined,
  };
}

function checkSingleVotePerBeing(votes: BeingVote[]): BeingInvariantCheck {
  const idCounts = new Map<string, number>();
  for (const v of votes) {
    idCounts.set(v.being.id, (idCounts.get(v.being.id) ?? 0) + 1);
  }
  const duplicates = [...idCounts.entries()].filter(([, count]) => count > 1);
  return {
    name: "single-vote-per-being",
    passed: duplicates.length === 0,
    detail: duplicates.length > 0 ? `Duplicate votes: ${duplicates.map(([id, c]) => `${id}×${c}`).join(", ")}` : undefined,
  };
}

function checkVoteWeightBounded(votes: BeingVote[]): BeingInvariantCheck {
  const invalid = votes.filter(v => v.weight < 0 || v.weight > 1);
  return {
    name: "vote-weight-bounded",
    passed: invalid.length === 0,
    detail: invalid.length > 0 ? `Out of bounds: ${invalid.map(v => `${v.being.id}=${v.weight}`).join(", ")}` : undefined,
  };
}

function checkDominantIsPresent(beings: BeingPresenceDetail[], dominantBeingId: string | null): BeingInvariantCheck {
  if (!dominantBeingId) {
    return { name: "dominant-is-present", passed: true };
  }
  const found = beings.some(b => b.id === dominantBeingId);
  return {
    name: "dominant-is-present",
    passed: found,
    detail: found ? undefined : `Dominant being "${dominantBeingId}" not found in beings list`,
  };
}

function checkOperatorAlwaysPresent(beings: BeingPresenceDetail[]): BeingInvariantCheck {
  const hasOperator = beings.some(b => b.id === "operator");
  return {
    name: "operator-always-present",
    passed: hasOperator,
    detail: hasOperator ? undefined : "Operator being is missing from presence map",
  };
}

// ── Main Validator ───────────────────────────────────────────────────

export function validateBeingConstitution(
  beings: BeingPresenceDetail[],
  votes: BeingVote[] = [],
  dominantBeingId: string | null = null,
): BeingInvariantReport {
  const checks: BeingInvariantCheck[] = [
    checkValidPosture(beings),
    checkValidPresenceMode(beings),
    checkValidAttentionLevel(beings),
    checkBoundedInfluence(beings),
    checkContinuityCoherent(beings),
    checkAnchorExists(beings),
    checkSingleVotePerBeing(votes),
    checkVoteWeightBounded(votes),
    checkDominantIsPresent(beings, dominantBeingId),
    checkOperatorAlwaysPresent(beings),
  ];

  const failedCount = checks.filter(c => !c.passed).length;
  return { allPassed: failedCount === 0, checks, failedCount };
}

// ── Frozen Laws ──────────────────────────────────────────────────────
//
// These are the frozen being laws. They cannot be overridden:
//
// LAW 1: Every being has a valid posture archetype.
// LAW 2: Every being has a valid presence mode.
// LAW 3: Every being has a valid attention level.
// LAW 4: Influence is bounded [0, 1].
// LAW 5: Continuity is coherent (streak >= 0).
// LAW 6: An anchor being must exist (streak >= 4, or sole being).
// LAW 7: Each being gets at most one active vote.
// LAW 8: Vote weight is bounded [0, 1].
// LAW 9: The dominant being must exist in the presence map.
// LAW 10: The operator being is always present.
