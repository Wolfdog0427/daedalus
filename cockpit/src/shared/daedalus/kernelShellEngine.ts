import type { AdaptationTuning } from "./sceneAdaptation";
import type { FabricDashboard } from "./governanceFabric";
import type { TuningCaps } from "./postAutonomy";
import { POST_AUTONOMY_DEFAULTS } from "./postAutonomy";
import { KERNEL_IDLE } from "./governanceKernel";
import { INVARIANT_REPORT_CLEAN } from "./kernelInvariants";
import { computeKernelState } from "./governanceKernelEngine";
import { validateInvariants } from "./kernelInvariantsEngine";
import type { KernelShellState, ShellStatus } from "./kernelShell";

/**
 * Single entry point for all kernel computation.
 *
 * 1. Computes the raw kernel state from effective tuning + dashboard.
 * 2. Validates all invariants against the computed state.
 * 3. If any invariant fails, returns KERNEL_IDLE with "degraded"
 *    status — preventing corrupted state from reaching the UI.
 * 4. If all pass, returns the computed state with "nominal" status.
 */
export function computeShellState(
  effectiveTuning: AdaptationTuning,
  dashboard: FabricDashboard,
  caps: TuningCaps = POST_AUTONOMY_DEFAULTS.caps,
): KernelShellState {
  const rawKernel = computeKernelState(effectiveTuning, dashboard);
  const invariants = validateInvariants(rawKernel, dashboard, effectiveTuning, caps);

  if (invariants.allPassed) {
    return {
      shellStatus: "nominal",
      kernel: rawKernel,
      invariants,
    };
  }

  return {
    shellStatus: "degraded",
    kernel: KERNEL_IDLE,
    invariants,
  };
}
