import type { DaedalusPosture } from "./contracts";
import type { OrchestrationIntent } from "./orchestration";
import type { OperatorAffectState } from "./operatorAffect";
import type { ContinuitySignalKind } from "./continuityNarrator";

/** Feature toggle: set to false to disable the conductor entirely. */
export const CONDUCTOR_ENABLED = true;

export type ConductorMode = "resting" | "attentive" | "escalated" | "celebrating";

export type ConductorTone = "neutral" | "focused" | "celebratory" | "alert";

export interface ConductorBadge {
  kind: ContinuitySignalKind;
  label: string;
}

export interface ConductorOutput {
  mode: ConductorMode;
  tone: ConductorTone;
  posture: DaedalusPosture;

  glowIntensity: number;
  motionIntensity: number;
  suppressAmbientPulse: boolean;

  continuityBadge: ConductorBadge | null;

  updatedAt: number;
}

export interface ConductorInputs {
  orchestrationIntent: OrchestrationIntent;
  orchestratedPosture: DaedalusPosture;
  arousal: number;
  focus: number;
  stability: number;
  operatorAffect: OperatorAffectState;
  continuitySignals: { kind: ContinuitySignalKind; label: string }[];
  glowIntensity: number;
}

export const CONDUCTOR_DEFAULTS: ConductorOutput = {
  mode: "resting",
  tone: "neutral",
  posture: "companion",
  glowIntensity: 0.3,
  motionIntensity: 0.5,
  suppressAmbientPulse: false,
  continuityBadge: null,
  updatedAt: 0,
};
