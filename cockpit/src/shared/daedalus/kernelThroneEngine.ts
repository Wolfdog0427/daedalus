import type { KernelHaloSnapshot } from "./kernelHalo";
import type { CrownState } from "./kernelCrown";
import type { ThroneView } from "./kernelThrone";

/**
 * Merges the halo (diagnostic) and crown (expressive) into a
 * single frozen ThroneView optimized for cockpit rendering.
 */
export function computeThroneView(
  halo: KernelHaloSnapshot,
  crown: CrownState,
): ThroneView {
  return Object.freeze({
    symbol: crown.symbol,
    glow: crown.glow,
    pulse: crown.pulse,
    stability: crown.stability,

    shellStatus: halo.shellStatus,
    kernelStatus: halo.kernelStatus,

    overrideCount: halo.overrideCount,
    activeOverrides: halo.activeOverrides,
    pendingCount: halo.pendingCount,
    activeTierCount: halo.activeTierCount,
    cappingApplied: halo.cappingApplied,

    invariantsHeld: halo.invariantsHeld,
    invariantsTotal: halo.invariantsTotal,
    invariantsPassed: halo.invariantsPassed,
  });
}
