import type { FusionScene } from "./fusion";
import type { OrchestratedScene } from "./sceneOrchestration";

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function easeInOutCubic(t: number): number {
  return t < 0.5
    ? 4 * t * t * t
    : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/**
 * Blends two fusion scenes together at a given raw progress (0–1).
 *
 * - Continuous values (glow, motion) interpolate along an eased curve.
 * - Discrete values (mode, tone, posture, badge, pulse suppression)
 *   snap at the blend midpoint (t >= 0.5).
 * - Narrative line snaps immediately when `narrativeSync` is true,
 *   otherwise at the midpoint like other discrete values.
 * - `sceneName` always reflects the target since the grammar already
 *   approved the transition.
 */
export function blendScenes(
  from: FusionScene,
  to: FusionScene,
  rawProgress: number,
  blendMs: number,
  narrativeSync: boolean,
): OrchestratedScene {
  const t = clamp01(rawProgress);
  const eased = easeInOutCubic(t);

  const pastMidpoint = t >= 0.5;
  const narrativeSnapped = narrativeSync || pastMidpoint;

  return {
    sceneName: to.sceneName,
    mode: pastMidpoint ? to.mode : from.mode,
    tone: pastMidpoint ? to.tone : from.tone,
    posture: pastMidpoint ? to.posture : from.posture,
    suppressAmbientPulse: pastMidpoint
      ? to.suppressAmbientPulse
      : from.suppressAmbientPulse,
    continuityBadge: pastMidpoint ? to.continuityBadge : from.continuityBadge,
    narrativeLine: narrativeSnapped ? to.narrativeLine : from.narrativeLine,
    glow: clamp01(lerp(from.glow, to.glow, eased)),
    motion: clamp01(lerp(from.motion, to.motion, eased)),
    progress: t,
    blendMs,
  };
}

/** Wrap a FusionScene as an already-resolved OrchestratedScene. */
export function snapScene(scene: FusionScene, blendMs = 0): OrchestratedScene {
  return { ...scene, progress: 1, blendMs };
}
