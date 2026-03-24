/** Feature toggle: set to false to disable analytics computation. */
export const SCENE_ANALYTICS_ENABLED = true;

export interface AnalyticsSnapshot {
  timestamp: number;

  sceneStability: number;           // 0–1: ratio of accepted transitions
  transitionSmoothness: number;     // 0–1: ratio of completed blends
  momentumVolatility: number;       // 0–1: variance of momentum values
  narrativeDensity: number;         // events per minute
  governorInterventionRate: number; // events per minute
  grammarRejectionRate: number;     // events per minute

  expressiveHealth: number;         // 0–1: weighted composite
}

export interface AnalyticsConfig {
  windowMs: number;
}

export const ANALYTICS_DEFAULTS: AnalyticsConfig = {
  windowMs: 5 * 60 * 1000, // 5 minutes
};

export const ANALYTICS_IDLE: AnalyticsSnapshot = {
  timestamp: 0,
  sceneStability: 1,
  transitionSmoothness: 1,
  momentumVolatility: 0,
  narrativeDensity: 0,
  governorInterventionRate: 0,
  grammarRejectionRate: 0,
  expressiveHealth: 1,
};
