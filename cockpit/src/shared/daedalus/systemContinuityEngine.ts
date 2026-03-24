import type {
  SystemContinuitySnapshot,
  ContinuityHealth,
} from "./systemContinuity";

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, v));
}

export interface SystemContinuityInput {
  /** ExpressiveField.stability — being-level coherence */
  beingStability: number;
  /** Number of beings currently present */
  beingCount: number;
  /** Best continuity streak among beings */
  bestStreak: number;
  /** Whether the continuity narrator detected any drift-recovery signals */
  driftSignalCount: number;
  /** Being id of the continuity anchor (longest streak), if any */
  anchorBeingId: string | null;

  /** OrchestrationState.affect.stability — orchestrated stability */
  orchestrationStability: number;
  /** OrchestrationState.transition.continuityBlend — blend smoothness */
  continuityBlend: number;

  /** EmbodiedPresenceSnapshot.continuity — embodied layer continuity */
  embodiedContinuity: number;
  /** EmbodiedPresenceSnapshot.motionGrammar — motion coherence */
  motionGrammar: number;

  /** Timeline momentum (0-1) — scene temporal coherence */
  timelineMomentum: number;
  /** Whether a persisted scene was successfully restored on startup */
  persistenceRestored: boolean;
}

/**
 * Identity continuity: how consistently Daedalus "is itself" over time.
 * Driven by being stability, streak depth, and whether beings are present.
 */
export function computeIdentityContinuity(
  beingStability: number,
  beingCount: number,
  bestStreak: number,
): number {
  if (beingCount === 0) return 0;
  const streakFactor = clamp(bestStreak / 25);
  return clamp(beingStability * 0.6 + streakFactor * 0.4);
}

/**
 * State continuity: how stable the orchestrated state is.
 * Blends orchestration stability with the transition smoothness.
 */
export function computeStateContinuity(
  orchestrationStability: number,
  continuityBlend: number,
): number {
  return clamp(orchestrationStability * 0.7 + continuityBlend * 0.3);
}

/**
 * Expressive continuity: how smooth and coherent the visual/motion
 * output is. Blends the embodied continuity with motion grammar.
 */
export function computeExpressiveContinuity(
  embodiedContinuity: number,
  motionGrammar: number,
): number {
  return clamp(embodiedContinuity * 0.6 + motionGrammar * 0.4);
}

/**
 * Temporal continuity: how well the system maintains coherence
 * across time boundaries. Driven by timeline momentum and
 * whether a persisted scene was restored.
 */
export function computeTemporalContinuity(
  timelineMomentum: number,
  persistenceRestored: boolean,
): number {
  const persistenceBonus = persistenceRestored ? 0.2 : 0;
  return clamp(timelineMomentum * 0.8 + persistenceBonus);
}

/**
 * Composite continuity score — a weighted blend of all four axes.
 */
export function computeComposite(
  identity: number,
  state: number,
  expressive: number,
  temporal: number,
): number {
  return clamp(
    identity * 0.3 + state * 0.3 + expressive * 0.2 + temporal * 0.2,
  );
}

export function deriveContinuityHealth(composite: number): ContinuityHealth {
  if (composite > 0.7) return "healthy";
  if (composite > 0.4) return "shifting";
  return "fragile";
}

export function computeSystemContinuity(
  input: SystemContinuityInput,
): SystemContinuitySnapshot {
  const identity = computeIdentityContinuity(
    input.beingStability,
    input.beingCount,
    input.bestStreak,
  );
  const state = computeStateContinuity(
    input.orchestrationStability,
    input.continuityBlend,
  );
  const expressive = computeExpressiveContinuity(
    input.embodiedContinuity,
    input.motionGrammar,
  );
  const temporal = computeTemporalContinuity(
    input.timelineMomentum,
    input.persistenceRestored,
  );
  const composite = computeComposite(identity, state, expressive, temporal);
  const health = deriveContinuityHealth(composite);

  return Object.freeze({
    identity,
    state,
    expressive,
    temporal,
    composite,
    health,
    driftSignalCount: input.driftSignalCount,
    anchorBeingId: input.anchorBeingId,
  });
}
