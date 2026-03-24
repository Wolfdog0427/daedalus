import type { KernelShellState } from "./kernelShell";
import type { KernelHaloSnapshot } from "./kernelHalo";

/**
 * Produces a frozen, flat, read-only snapshot from the shell state.
 * This is the single view that all HUD and diagnostic surfaces consume.
 */
export function computeHaloSnapshot(shell: KernelShellState): KernelHaloSnapshot {
  const { kernel, invariants, shellStatus } = shell;

  const failedInvariants = invariants.checks
    .filter((c) => !c.passed)
    .map((c) => c.name);

  return Object.freeze({
    shellStatus,
    kernelStatus: kernel.status,
    overrideCount: kernel.overrideCount,
    activeOverrides: Object.freeze([...kernel.activeOverrides]),
    activeTierCount: kernel.activeTierCount,
    pendingCount: kernel.pendingCount,
    cappingApplied: kernel.cappingApplied,
    invariantsHeld: invariants.checks.length - invariants.failedCount,
    invariantsTotal: invariants.checks.length,
    invariantsPassed: invariants.allPassed,
    failedInvariants: Object.freeze(failedInvariants),
  });
}
