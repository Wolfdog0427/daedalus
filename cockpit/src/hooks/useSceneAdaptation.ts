import { useMemo } from "react";
import type { AnalyticsSnapshot } from "../shared/daedalus/sceneAnalytics";
import type { AdaptationSnapshot } from "../shared/daedalus/sceneAdaptation";
import { SCENE_ADAPTATION_ENABLED, ADAPTATION_IDLE } from "../shared/daedalus/sceneAdaptation";
import { computeAdaptation } from "../shared/daedalus/sceneAdaptationEngine";

/**
 * Derives adaptive tuning from the current analytics snapshot.
 * Recomputes whenever the analytics reference changes.
 */
export function useSceneAdaptation(
  analytics: AnalyticsSnapshot,
): AdaptationSnapshot {
  return useMemo(() => {
    if (!SCENE_ADAPTATION_ENABLED) return { ...ADAPTATION_IDLE, timestamp: Date.now() };
    return computeAdaptation(analytics);
  }, [analytics]);
}
