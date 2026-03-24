import type { TelemetryEvent } from "./sceneTelemetry";
import type { AnalyticsSnapshot, AnalyticsConfig } from "./sceneAnalytics";
import { ANALYTICS_DEFAULTS, ANALYTICS_IDLE } from "./sceneAnalytics";

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

/**
 * Computes an analytics snapshot from a set of telemetry events
 * within the configured time window.
 *
 * All inputs are value types — no side effects, no subscriptions.
 */
export function computeAnalytics(
  events: TelemetryEvent[],
  config: AnalyticsConfig = ANALYTICS_DEFAULTS,
  now: number = Date.now(),
): AnalyticsSnapshot {
  const cutoff = now - config.windowMs;
  const windowed = events.filter((e) => e.timestamp >= cutoff);

  if (windowed.length === 0) {
    return { ...ANALYTICS_IDLE, timestamp: now };
  }

  const windowMinutes = config.windowMs / 60_000;

  const byType = (type: string) =>
    windowed.filter((e) => e.type === type);

  const transitions = byType("scene-transition").length;
  const rejections = byType("scene-rejected").length;
  const blendStarts = byType("blend-start").length;
  const blendCompletes = byType("blend-complete").length;
  const momentumEvents = byType("momentum");
  const narrativeCount = byType("narrative").length;
  const governorLocks = byType("governor-lock").length;
  const governorCooldowns = byType("governor-cooldown").length;

  // ── Scene stability: ratio of accepted transitions ──
  const totalAttempts = transitions + rejections;
  const sceneStability = totalAttempts === 0
    ? 1
    : clamp01(transitions / totalAttempts);

  // ── Transition smoothness: ratio of blends that completed ──
  const transitionSmoothness = blendStarts === 0
    ? 1
    : clamp01(blendCompletes / blendStarts);

  // ── Momentum volatility: normalized variance of momentum values ──
  let momentumVolatility = 0;
  if (momentumEvents.length >= 2) {
    const values = momentumEvents.map(
      (e) => (typeof e.payload.momentum === "number" ? e.payload.momentum : 0),
    );
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance =
      values.reduce((a, v) => a + (v - mean) ** 2, 0) / values.length;
    momentumVolatility = clamp01(variance * 4);
  }

  // ── Rates (events per minute) ──
  const narrativeDensity = narrativeCount / windowMinutes;
  const governorInterventionRate =
    (governorLocks + governorCooldowns) / windowMinutes;
  const grammarRejectionRate = rejections / windowMinutes;

  // ── Composite expressive health ──
  // Weights sum to 1.0:
  //   stability        0.25
  //   smoothness       0.25
  //   (1-volatility)   0.20
  //   (1-normGovRate)  0.15
  //   (1-normRejRate)  0.15
  const normGov = clamp01(governorInterventionRate / 10);
  const normRej = clamp01(grammarRejectionRate / 5);

  const expressiveHealth = clamp01(
    sceneStability * 0.25 +
    transitionSmoothness * 0.25 +
    (1 - momentumVolatility) * 0.20 +
    (1 - normGov) * 0.15 +
    (1 - normRej) * 0.15,
  );

  return {
    timestamp: now,
    sceneStability,
    transitionSmoothness,
    momentumVolatility,
    narrativeDensity,
    governorInterventionRate,
    grammarRejectionRate,
    expressiveHealth,
  };
}
