/**
 * System Continuity — a unified read-only view of Daedalus's
 * coherence across four axes: identity (being consistency),
 * state (orchestration stability), expressive (glow/motion
 * smoothness), and temporal (scene persistence across time).
 *
 * Derived from the expressive field, orchestration, continuity
 * signals, and scene persistence. Feeds into the Throne for
 * display but never into governance logic.
 */

export type ContinuityHealth = "healthy" | "shifting" | "fragile";

export interface SystemContinuitySnapshot {
  readonly identity: number;
  readonly state: number;
  readonly expressive: number;
  readonly temporal: number;

  readonly composite: number;
  readonly health: ContinuityHealth;
  readonly driftSignalCount: number;
  readonly anchorBeingId: string | null;
}

export const SYSTEM_CONTINUITY_IDLE: SystemContinuitySnapshot = Object.freeze({
  identity: 1,
  state: 1,
  expressive: 1,
  temporal: 1,

  composite: 1,
  health: "healthy" as ContinuityHealth,
  driftSignalCount: 0,
  anchorBeingId: null,
});
