import { useMemo } from "react";
import type { TelemetryEvent } from "../shared/daedalus/sceneTelemetry";
import type { AnalyticsSnapshot } from "../shared/daedalus/sceneAnalytics";
import { SCENE_ANALYTICS_ENABLED, ANALYTICS_DEFAULTS, ANALYTICS_IDLE } from "../shared/daedalus/sceneAnalytics";
import { computeAnalytics } from "../shared/daedalus/sceneAnalyticsEngine";

/**
 * Derives an analytics snapshot from the current telemetry buffer.
 * Recomputes whenever the telemetry array reference changes
 * (i.e. when new events are recorded).
 */
export function useSceneAnalytics(
  telemetry: TelemetryEvent[],
): AnalyticsSnapshot {
  return useMemo(() => {
    if (!SCENE_ANALYTICS_ENABLED) return { ...ANALYTICS_IDLE, timestamp: Date.now() };
    return computeAnalytics(telemetry, ANALYTICS_DEFAULTS);
  }, [telemetry]);
}
