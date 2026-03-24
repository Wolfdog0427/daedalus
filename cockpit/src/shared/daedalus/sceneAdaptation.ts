/** Feature toggle: set to false to disable adaptive tuning. */
export const SCENE_ADAPTATION_ENABLED = true;

export interface AdaptationReason {
  trigger: string;
  action: string;
}

/**
 * Optional overrides computed from analytics that modulate
 * each expressive subsystem. Undefined fields mean "no change".
 */
export interface AdaptationTuning {
  // Governor
  governorCooldownMs?: number;
  governorEscalationLockMs?: number;

  // Timeline
  timelineMomentumHalfLifeMs?: number;

  // Narrative
  narrativeMinIntervalMs?: number;

  // Scene Grammar
  grammarDefaultDwellMs?: number;
  grammarDefaultBlendMs?: number;
}

export interface AdaptationSnapshot {
  timestamp: number;
  tuning: AdaptationTuning;
  reasons: AdaptationReason[];
}

export const ADAPTATION_IDLE: AdaptationSnapshot = {
  timestamp: 0,
  tuning: {},
  reasons: [],
};
