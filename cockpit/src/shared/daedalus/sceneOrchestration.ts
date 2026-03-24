import type { FusionScene } from "./fusion";

/** Feature toggle: set to false to bypass scene blending. */
export const SCENE_ORCHESTRATION_ENABLED = true;

/**
 * A FusionScene enriched with blend progress metadata.
 * During a transition, continuous values (glow, motion) are interpolated
 * and discrete values (mode, tone, posture) snap at the midpoint.
 */
export interface OrchestratedScene extends FusionScene {
  /** 0–1: how far through the current blend we are (1 = fully arrived). */
  progress: number;
  /** Total blend duration for this transition in milliseconds. */
  blendMs: number;
}
