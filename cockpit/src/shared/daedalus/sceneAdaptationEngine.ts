import type { AnalyticsSnapshot } from "./sceneAnalytics";
import type { AdaptationSnapshot, AdaptationTuning, AdaptationReason } from "./sceneAdaptation";

/**
 * Examines analytics and produces adaptive tuning overrides.
 *
 * This is NOT personality or emotion — it is parameter tuning
 * that stabilizes the expressive system under stress and
 * loosens constraints when healthy.
 */
export function computeAdaptation(
  analytics: AnalyticsSnapshot,
  now: number = Date.now(),
): AdaptationSnapshot {
  const tuning: AdaptationTuning = {};
  const reasons: AdaptationReason[] = [];

  // ── 1. High momentum volatility → increase timeline smoothing ──
  if (analytics.momentumVolatility > 0.5) {
    tuning.timelineMomentumHalfLifeMs = 9000;
    reasons.push({ trigger: "high-volatility", action: "increased timeline smoothing" });
  }

  // ── 2. Grammar rejections climbing → increase dwell times ──
  if (analytics.grammarRejectionRate > 0.3) {
    tuning.grammarDefaultDwellMs = 1400;
    reasons.push({ trigger: "frequent-rejections", action: "increased scene dwell" });
  }

  // ── 3. Narrative density spike → widen rate limit ──
  if (analytics.narrativeDensity > 3) {
    tuning.narrativeMinIntervalMs = 5500;
    reasons.push({ trigger: "narrative-density", action: "widened narrative interval" });
  }

  // ── 4. Governor intervention rate high → widen cooldowns ──
  if (analytics.governorInterventionRate > 1.5) {
    tuning.governorCooldownMs = 1400;
    tuning.governorEscalationLockMs = 3500;
    reasons.push({ trigger: "governor-busy", action: "widened governor cooldowns" });
  }

  // ── 5. Low expressive health → shift to calm ──
  if (analytics.expressiveHealth < 0.4) {
    tuning.governorCooldownMs = Math.max(tuning.governorCooldownMs ?? 0, 1600);
    tuning.governorEscalationLockMs = Math.max(tuning.governorEscalationLockMs ?? 0, 4000);
    tuning.grammarDefaultBlendMs = 700;
    tuning.grammarDefaultDwellMs = Math.max(tuning.grammarDefaultDwellMs ?? 0, 1400);
    tuning.timelineMomentumHalfLifeMs = Math.max(tuning.timelineMomentumHalfLifeMs ?? 0, 10000);
    reasons.push({ trigger: "low-health", action: "calm preset" });
  }

  // ── 6. High expressive health → allow responsiveness ──
  if (analytics.expressiveHealth > 0.85) {
    if (!tuning.governorCooldownMs) tuning.governorCooldownMs = 500;
    if (!tuning.governorEscalationLockMs) tuning.governorEscalationLockMs = 1800;
    if (!tuning.grammarDefaultBlendMs) tuning.grammarDefaultBlendMs = 400;
    reasons.push({ trigger: "high-health", action: "responsive preset" });
  }

  return { timestamp: now, tuning, reasons };
}
