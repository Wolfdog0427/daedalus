/**
 * Embodied Presence — a unified read-only view of Daedalus's
 * living presence: physiology, motion, glow, and continuity
 * derived from the being / expressive field / connectivity layers.
 *
 * Feeds into the Throne for display but never into governance logic.
 */

export interface NodeGlow {
  readonly id: string;
  readonly glow: number;
}

export interface EmbodiedPresenceSnapshot {
  readonly embodiment: number;
  readonly motionGrammar: number;
  readonly unifiedGlow: number;
  readonly continuity: number;

  readonly beingCount: number;
  readonly dominantBeingId: string | null;
  readonly posture: string;

  readonly nodeGlows: readonly NodeGlow[];
}

export const EMBODIED_IDLE: EmbodiedPresenceSnapshot = Object.freeze({
  embodiment: 0,
  motionGrammar: 0,
  unifiedGlow: 0,
  continuity: 1,

  beingCount: 0,
  dominantBeingId: null,
  posture: "observer",

  nodeGlows: Object.freeze([]) as readonly NodeGlow[],
});
