import { useMemo } from "react";
import type { AdaptationTuning } from "../shared/daedalus/sceneAdaptation";
import type { TierName, GovernanceFabricSnapshot } from "../shared/daedalus/postAutonomy";
import { POST_AUTONOMY_ENABLED, POST_AUTONOMY_DEFAULTS, FABRIC_IDLE } from "../shared/daedalus/postAutonomy";
import { consolidate } from "../shared/daedalus/postAutonomyEngine";

export interface TierTunings {
  adaptation: AdaptationTuning;
  "tier-0": AdaptationTuning;
  "tier-1": AdaptationTuning;
  "tier-3": AdaptationTuning;
  "tier-4": AdaptationTuning;
  "tier-5": AdaptationTuning;
}

/**
 * Post-Autonomy Transition Layer hook.
 *
 * Takes the final merged tuning and the individual tier tunings,
 * applies safety caps, detects escalation, and returns a unified
 * governance fabric snapshot with the capped effective tuning.
 */
export function usePostAutonomy(
  mergedTuning: AdaptationTuning,
  tiers: TierTunings,
): GovernanceFabricSnapshot {
  return useMemo(() => {
    if (!POST_AUTONOMY_ENABLED) return { ...FABRIC_IDLE, effectiveTuning: mergedTuning };
    return consolidate(mergedTuning, tiers as Partial<Record<TierName, AdaptationTuning>>, POST_AUTONOMY_DEFAULTS);
  }, [mergedTuning, tiers]);
}
