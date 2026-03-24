import type { EmbodiedPresenceSnapshot, NodeGlow } from "./embodiedPresence";

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, v));
}

export interface EmbodiedPresenceInput {
  beingCount: number;
  dominantBeingId: string | null;
  posture: string;
  arousal: number;
  focus: number;
  stability: number;
  sceneGlow: number;
  sceneMotion: number;
  connectivityNodes: readonly { id: string; health: number; trusted: boolean }[];
}

/**
 * Motion grammar: a blended signal of how "alive" the embodiment
 * feels, combining arousal (energy) with stability (coherence).
 */
export function computeMotionGrammar(arousal: number, stability: number): number {
  return clamp(arousal * 0.6 + stability * 0.4);
}

/**
 * Unified glow: blends the scene's visual glow with the motion
 * grammar to produce a single expressive intensity value.
 */
export function unifyGlow(sceneGlow: number, motionGrammar: number): number {
  return clamp(sceneGlow * 0.7 + motionGrammar * 0.3);
}

/**
 * Embodiment score: how present and inhabited the system feels.
 * Driven by being count, focus, and arousal.
 */
export function computeEmbodiment(
  beingCount: number,
  focus: number,
  arousal: number,
): number {
  if (beingCount === 0) return 0;
  const countFactor = clamp(beingCount * 0.25);
  return clamp(countFactor * 0.3 + focus * 0.4 + arousal * 0.3);
}

/**
 * Per-node glow: derived from each node's health and trust status.
 */
export function computeNodeGlows(
  nodes: readonly { id: string; health: number; trusted: boolean }[],
): NodeGlow[] {
  return nodes.map((n) =>
    Object.freeze({
      id: n.id,
      glow: clamp(n.health * 0.8 + (n.trusted ? 0.2 : 0)),
    }),
  );
}

export function computeEmbodiedPresence(
  input: EmbodiedPresenceInput,
): EmbodiedPresenceSnapshot {
  const motionGrammar = computeMotionGrammar(input.arousal, input.stability);
  const unifiedGlow = unifyGlow(input.sceneGlow, motionGrammar);
  const embodiment = computeEmbodiment(input.beingCount, input.focus, input.arousal);
  const nodeGlows = computeNodeGlows(input.connectivityNodes);

  return Object.freeze({
    embodiment,
    motionGrammar,
    unifiedGlow,
    continuity: input.stability,

    beingCount: input.beingCount,
    dominantBeingId: input.dominantBeingId,
    posture: input.posture,

    nodeGlows: Object.freeze(nodeGlows),
  });
}
