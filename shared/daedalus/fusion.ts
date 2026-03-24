import type { DaedalusPosture } from "./contracts";
import type { ConductorMode, ConductorTone, ConductorBadge } from "./conductor";

/** Feature toggle: set to false to disable fusion scene computation. */
export const FUSION_ENABLED = true;

export type FusionSceneName =
  | "apex"
  | "rising"
  | "waning"
  | "settling"
  | "alert"
  | "celebrating"
  | "focus"
  | "exploring"
  | "idle";

export interface FusionScene {
  sceneName: FusionSceneName;
  mode: ConductorMode;
  tone: ConductorTone;
  posture: DaedalusPosture;
  glow: number;
  motion: number;
  suppressAmbientPulse: boolean;
  continuityBadge: ConductorBadge | null;
  narrativeLine: string | null;
}

export const FUSION_SCENE_IDLE: FusionScene = {
  sceneName: "idle",
  mode: "resting",
  tone: "neutral",
  posture: "companion",
  glow: 0.3,
  motion: 0.5,
  suppressAmbientPulse: false,
  continuityBadge: null,
  narrativeLine: null,
};
