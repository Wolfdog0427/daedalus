import type { AdaptationTuning } from "./sceneAdaptation";
import type {
  TierName,
  TuningCaps,
  PostAutonomyConfig,
  GovernanceFabricSnapshot,
} from "./postAutonomy";
import { POST_AUTONOMY_DEFAULTS } from "./postAutonomy";

/**
 * Identifies which tiers have non-empty approved tuning.
 */
export function identifyActiveTiers(
  tiers: Partial<Record<TierName, AdaptationTuning>>,
): TierName[] {
  const active: TierName[] = [];
  for (const [name, tuning] of Object.entries(tiers) as [TierName, AdaptationTuning][]) {
    if (tuning && Object.keys(tuning).length > 0) {
      active.push(name);
    }
  }
  return active;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * Clamps every defined field in the merged tuning to safe bounds.
 * Returns the capped tuning and whether any capping was applied.
 */
export function capTuning(
  tuning: AdaptationTuning,
  caps: TuningCaps = POST_AUTONOMY_DEFAULTS.caps,
): { capped: AdaptationTuning; applied: boolean } {
  let applied = false;
  const capped: AdaptationTuning = { ...tuning };

  const fields: { key: keyof AdaptationTuning; cap: keyof TuningCaps }[] = [
    { key: "governorCooldownMs", cap: "governorCooldownMs" },
    { key: "governorEscalationLockMs", cap: "governorEscalationLockMs" },
    { key: "timelineMomentumHalfLifeMs", cap: "timelineMomentumHalfLifeMs" },
    { key: "narrativeMinIntervalMs", cap: "narrativeMinIntervalMs" },
    { key: "grammarDefaultDwellMs", cap: "grammarDefaultDwellMs" },
    { key: "grammarDefaultBlendMs", cap: "grammarDefaultBlendMs" },
  ];

  for (const { key, cap } of fields) {
    const val = capped[key];
    if (val === undefined) continue;
    const [min, max] = caps[cap];
    const clamped = clamp(val, min, max);
    if (clamped !== val) {
      applied = true;
      (capped as Record<string, number>)[key] = clamped;
    }
  }

  return { capped, applied };
}

/**
 * Produces a unified governance fabric snapshot:
 * - Which tiers are active
 * - Whether escalation (too many simultaneous tiers) is detected
 * - The safety-capped effective tuning
 */
export function consolidate(
  mergedTuning: AdaptationTuning,
  tiers: Partial<Record<TierName, AdaptationTuning>>,
  config: PostAutonomyConfig = POST_AUTONOMY_DEFAULTS,
): GovernanceFabricSnapshot {
  const activeTiers = identifyActiveTiers(tiers);
  const activeTierCount = activeTiers.length;
  const escalationDetected = activeTierCount > config.maxActiveTiers;

  const { capped, applied } = capTuning(mergedTuning, config.caps);

  return {
    activeTierCount,
    activeTiers,
    escalationDetected,
    cappingApplied: applied,
    effectiveTuning: capped,
  };
}
