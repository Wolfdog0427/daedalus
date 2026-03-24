/** Feature toggle: set to false to disable timeline modulation entirely. */
export const TIMELINE_ENABLED = true;

export type TimelinePhase = "idle" | "settling" | "rising" | "peak" | "cooldown";

export interface TimelineEvent {
  timestamp: number;
  kind: "mode" | "tone" | "posture" | "badge";
}

export interface TimelineSnapshot {
  phase: TimelinePhase;
  momentum: number;
  eventCount: number;
}

export interface TimelineConfig {
  windowMs: number;
  momentumHalfLifeMs: number;
  peakThreshold: number;
  cooldownThreshold: number;
}

export const TIMELINE_DEFAULTS: TimelineConfig = {
  windowMs: 8000,
  momentumHalfLifeMs: 6000,
  peakThreshold: 0.75,
  cooldownThreshold: 0.35,
};

export const TIMELINE_SNAPSHOT_IDLE: TimelineSnapshot = {
  phase: "idle",
  momentum: 0,
  eventCount: 0,
};
