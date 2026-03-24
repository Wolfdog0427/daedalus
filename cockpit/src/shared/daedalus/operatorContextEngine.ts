import type { OperatorMode, OperatorContextSnapshot } from "./operatorContext";

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, v));
}

export interface OperatorContextInput {
  activePanel: string;
  affectEffective: string;
  affectPinned: boolean;
  currentIntent: string | null;
  postureNudge: string | null;
  governorEnabled: boolean;
  governorPreset: string;
  pendingProposals: number;
}

/**
 * Derives the operator mode from affect + intent + overrides.
 *
 * Priority:
 *   1. override — any active operator override
 *   2. explore  — exploration intent or exploratory affect
 *   3. review   — governance panel is active
 *   4. focus    — default working mode
 */
export function deriveMode(input: OperatorContextInput): OperatorMode {
  if (input.affectPinned || input.postureNudge !== null || !input.governorEnabled) {
    return "override";
  }
  if (input.currentIntent === "exploration" || input.affectEffective === "exploratory") {
    return "explore";
  }
  if (input.activePanel === "governance") {
    return "review";
  }
  return "focus";
}

/**
 * Counts active operator overrides (affect pin, posture nudge,
 * governor disabled, non-default preset).
 */
export function countOverrides(input: OperatorContextInput): number {
  let count = 0;
  if (input.affectPinned) count++;
  if (input.postureNudge !== null) count++;
  if (!input.governorEnabled) count++;
  if (input.governorPreset !== "default") count++;
  return count;
}

/**
 * Sovereignty score (0–1): how much control the operator has asserted.
 * Starts at 1 (full sovereignty) and decreases with pending proposals
 * that have not yet been reviewed.
 */
export function computeSovereignty(
  overrideCount: number,
  pendingProposals: number,
): number {
  const pendingPenalty = pendingProposals * 0.1;
  const overrideBoost = Math.min(overrideCount * 0.05, 0.15);
  return clamp(1 - pendingPenalty + overrideBoost);
}

export function computeOperatorContext(
  input: OperatorContextInput,
): OperatorContextSnapshot {
  const mode = deriveMode(input);
  const overrideCount = countOverrides(input);
  const sovereignty = computeSovereignty(overrideCount, input.pendingProposals);

  return Object.freeze({
    mode,
    focus: input.activePanel,
    intent: input.currentIntent,
    affect: input.affectEffective,

    affectPinned: input.affectPinned,
    postureNudged: input.postureNudge !== null,
    governorOverridden: !input.governorEnabled,
    overrideCount,
    pendingProposals: input.pendingProposals,

    sovereignty,
  });
}
