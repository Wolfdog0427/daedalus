import type { AdaptationTuning } from "./sceneAdaptation";
import type { FabricDashboard } from "./governanceFabric";
import type { KernelState, KernelStatus } from "./governanceKernel";

/**
 * Computes the irreducible kernel state from the effective tuning
 * (post-cap) and the governance fabric dashboard.
 */
export function computeKernelState(
  effectiveTuning: AdaptationTuning,
  dashboard: FabricDashboard,
): KernelState {
  const activeOverrides = (Object.keys(effectiveTuning) as (keyof AdaptationTuning)[])
    .filter((k) => effectiveTuning[k] !== undefined);
  const overrideCount = activeOverrides.length;

  let status: KernelStatus = "clean";
  if (dashboard.escalationDetected || dashboard.health.label === "overloaded") {
    status = "escalated";
  } else if (overrideCount > 0) {
    status = "tuned";
  }

  return {
    status,
    overrideCount,
    activeOverrides,
    activeTierCount: dashboard.activeTierCount,
    pendingCount: dashboard.pendingCount,
    cappingApplied: dashboard.cappingApplied,
  };
}
