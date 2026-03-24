import type { DaedalusPosture } from "./contracts";

export type OrchestrationIntent = "idle" | "guiding" | "supporting" | "alert" | "escalating";

export type PostureShift = "none" | "soft" | "hard";

export interface OrchestrationTransition {
  postureShift: PostureShift;
  continuityBlend: number;
}

export interface OrchestrationAffect {
  arousal: number;
  focus: number;
  stability: number;
}

export interface OrchestrationState {
  orchestratedPosture: DaedalusPosture;
  affect: OrchestrationAffect;
  transition: OrchestrationTransition;
  intent: OrchestrationIntent;
  updatedAt: number;
}

export const ORCHESTRATION_DEFAULTS: OrchestrationState = {
  orchestratedPosture: "companion",
  affect: { arousal: 0, focus: 0, stability: 1 },
  transition: { postureShift: "none", continuityBlend: 1 },
  intent: "idle",
  updatedAt: 0,
};
