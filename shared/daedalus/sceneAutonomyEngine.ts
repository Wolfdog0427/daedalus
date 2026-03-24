import type { AnalyticsSnapshot } from "./sceneAnalytics";
import type { AdaptationTuning } from "./sceneAdaptation";
import type { AutonomyProposal, AutonomyConfig } from "./sceneAutonomy";
import { AUTONOMY_DEFAULTS } from "./sceneAutonomy";

/**
 * Evaluates analytics against autonomy thresholds and produces
 * a bounded proposal if issues are detected. Returns null when
 * no proposal is warranted (rate-limited or within thresholds).
 *
 * This function never modifies state — it only recommends.
 * Application requires explicit operator approval.
 */
export function evaluateAutonomy(
  analytics: AnalyticsSnapshot,
  lastProposalAt: number,
  nextId: number,
  config: AutonomyConfig = AUTONOMY_DEFAULTS,
  now: number = Date.now(),
): AutonomyProposal | null {
  if (now - lastProposalAt < config.minIntervalMs) return null;

  const reasons: string[] = [];
  const recommended: AdaptationTuning = {};

  // 1. High momentum volatility → increase timeline smoothing
  if (analytics.momentumVolatility > config.volatilityThreshold) {
    reasons.push("High momentum volatility");
    recommended.timelineMomentumHalfLifeMs = 10000;
  }

  // 2. Frequent grammar rejections → increase dwell times
  if (analytics.grammarRejectionRate > config.rejectionRateThreshold) {
    reasons.push("Frequent scene rejections");
    recommended.grammarDefaultDwellMs = 1500;
  }

  // 3. Governor overactive → widen cooldowns
  if (analytics.governorInterventionRate > config.governorRateThreshold) {
    reasons.push("Governor intervening frequently");
    recommended.governorCooldownMs = 1600;
    recommended.governorEscalationLockMs = 4000;
  }

  // 4. Low expressive health → comprehensive calm shift
  if (analytics.expressiveHealth < config.healthThreshold) {
    reasons.push("Low expressive health");
    recommended.governorCooldownMs = Math.max(recommended.governorCooldownMs ?? 0, 1800);
    recommended.governorEscalationLockMs = Math.max(recommended.governorEscalationLockMs ?? 0, 4500);
    recommended.grammarDefaultBlendMs = 800;
    recommended.grammarDefaultDwellMs = Math.max(recommended.grammarDefaultDwellMs ?? 0, 1600);
    recommended.narrativeMinIntervalMs = 6000;
    recommended.timelineMomentumHalfLifeMs = Math.max(
      recommended.timelineMomentumHalfLifeMs ?? 0,
      12000,
    );
  }

  if (reasons.length === 0) return null;

  return {
    id: nextId,
    timestamp: now,
    reason: reasons.join("; "),
    recommended,
  };
}

/**
 * Merges operator-approved autonomy tuning on top of automatic
 * adaptation tuning. Autonomy overrides take priority since
 * they carry explicit operator consent.
 */
export function mergeAutonomyTuning(
  adaptationTuning: AdaptationTuning,
  approvedTuning: AdaptationTuning,
): AdaptationTuning {
  const merged: AdaptationTuning = { ...adaptationTuning };
  for (const key of Object.keys(approvedTuning) as (keyof AdaptationTuning)[]) {
    if (approvedTuning[key] !== undefined) {
      (merged as Record<string, unknown>)[key] = approvedTuning[key];
    }
  }
  return merged;
}
