/** Feature toggle: set to false to disable post-autonomy capping. */
export const POST_AUTONOMY_ENABLED = true;

import type { AdaptationTuning } from "./sceneAdaptation";

export type TierName =
  | "adaptation"
  | "tier-0"
  | "tier-1"
  | "tier-3"
  | "tier-4"
  | "tier-5";

/**
 * Two-sided clamps for every tuning parameter.
 * Prevents any combination of autonomy tiers from
 * pushing the system into a sluggish or jittery state.
 */
export interface TuningCaps {
  governorCooldownMs: [min: number, max: number];
  governorEscalationLockMs: [min: number, max: number];
  timelineMomentumHalfLifeMs: [min: number, max: number];
  narrativeMinIntervalMs: [min: number, max: number];
  grammarDefaultDwellMs: [min: number, max: number];
  grammarDefaultBlendMs: [min: number, max: number];
}

export interface PostAutonomyConfig {
  maxActiveTiers: number;
  caps: TuningCaps;
}

export const POST_AUTONOMY_DEFAULTS: PostAutonomyConfig = {
  maxActiveTiers: 4,
  caps: {
    governorCooldownMs: [400, 2200],
    governorEscalationLockMs: [1500, 5000],
    timelineMomentumHalfLifeMs: [3000, 16000],
    narrativeMinIntervalMs: [1500, 10000],
    grammarDefaultDwellMs: [500, 2200],
    grammarDefaultBlendMs: [150, 1000],
  },
};

/**
 * Unified snapshot of the governance fabric — what the
 * operator sees in the HUD as the final autonomy state.
 */
export interface GovernanceFabricSnapshot {
  activeTierCount: number;
  activeTiers: TierName[];
  escalationDetected: boolean;
  cappingApplied: boolean;
  effectiveTuning: AdaptationTuning;
}

export const FABRIC_IDLE: GovernanceFabricSnapshot = {
  activeTierCount: 0,
  activeTiers: [],
  escalationDetected: false,
  cappingApplied: false,
  effectiveTuning: {},
};
