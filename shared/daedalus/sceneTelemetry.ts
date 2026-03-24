/** Feature toggle: set to false to disable telemetry recording. */
export const SCENE_TELEMETRY_ENABLED = true;

export type TelemetryEventType =
  | "scene-transition"
  | "scene-rejected"
  | "blend-start"
  | "blend-complete"
  | "momentum"
  | "narrative"
  | "governor-lock"
  | "governor-cooldown"
  | "persistence-restore";

export interface TelemetryEvent {
  id: number;
  timestamp: number;
  type: TelemetryEventType;
  payload: Record<string, unknown>;
}

export interface TelemetryConfig {
  maxEvents: number;
}

export const TELEMETRY_DEFAULTS: TelemetryConfig = {
  maxEvents: 200,
};
