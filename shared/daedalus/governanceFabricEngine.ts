import type { AutonomyDecision } from "./sceneAutonomy";
import type { GovernanceFabricSnapshot } from "./postAutonomy";
import type {
  FabricHealth,
  FabricHealthLabel,
  FabricDashboard,
  FabricConfig,
} from "./governanceFabric";
import { FABRIC_CONFIG_DEFAULTS, FABRIC_HEALTH_IDLE } from "./governanceFabric";

/**
 * Computes governance health from a flat array of decisions
 * across all autonomy tiers.
 */
export function computeHealth(
  decisions: AutonomyDecision[],
  config: FabricConfig = FABRIC_CONFIG_DEFAULTS,
  now: number = Date.now(),
): FabricHealth {
  const cutoff = now - config.windowMs;
  const windowed = decisions.filter((d) => d.timestamp >= cutoff);

  if (windowed.length === 0) return FABRIC_HEALTH_IDLE;

  const approvals = windowed.filter((d) => d.approved).length;
  const rejections = windowed.length - approvals;
  const minutes = config.windowMs / 60_000;
  const decisionRate = windowed.length / minutes;

  let label: FabricHealthLabel = "stable";
  if (decisionRate >= config.overloadedThreshold) label = "overloaded";
  else if (decisionRate >= config.busyThreshold) label = "busy";
  else if (windowed.length > 0) label = "active";

  return {
    label,
    totalDecisions: windowed.length,
    approvals,
    rejections,
    decisionRate,
  };
}

/**
 * Builds the complete governance dashboard by combining
 * the post-autonomy fabric snapshot (caps, tiers, escalation)
 * with health computed from cross-tier decision history.
 */
export function buildDashboard(
  fabric: GovernanceFabricSnapshot,
  decisions: AutonomyDecision[],
  pendingCount: number,
  config: FabricConfig = FABRIC_CONFIG_DEFAULTS,
  now: number = Date.now(),
): FabricDashboard {
  return {
    health: computeHealth(decisions, config, now),
    activeTierCount: fabric.activeTierCount,
    activeTiers: [...fabric.activeTiers],
    escalationDetected: fabric.escalationDetected,
    cappingApplied: fabric.cappingApplied,
    pendingCount,
  };
}
