/** Feature toggle: set to false to disable autonomy proposals. */
export const SCENE_AUTONOMY_ENABLED = true;

import type { AdaptationTuning } from "./sceneAdaptation";

export interface AutonomyProposal {
  id: number;
  timestamp: number;
  reason: string;
  recommended: AdaptationTuning;
}

export interface AutonomyDecision {
  proposalId: number;
  approved: boolean;
  timestamp: number;
}

export interface AutonomyConfig {
  minIntervalMs: number;
  volatilityThreshold: number;
  healthThreshold: number;
  rejectionRateThreshold: number;
  governorRateThreshold: number;
}

export const AUTONOMY_DEFAULTS: AutonomyConfig = {
  minIntervalMs: 8000,
  volatilityThreshold: 0.55,
  healthThreshold: 0.45,
  rejectionRateThreshold: 0.5,
  governorRateThreshold: 2.0,
};
