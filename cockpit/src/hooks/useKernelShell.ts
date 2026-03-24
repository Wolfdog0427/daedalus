import { useMemo, useCallback } from "react";
import type { AdaptationTuning } from "../shared/daedalus/sceneAdaptation";
import type { FabricDashboard } from "../shared/daedalus/governanceFabric";
import type { KernelShellState } from "../shared/daedalus/kernelShell";
import type { KernelHaloSnapshot } from "../shared/daedalus/kernelHalo";
import type { CrownState } from "../shared/daedalus/kernelCrown";
import type { ThroneView } from "../shared/daedalus/kernelThrone";
import { KERNEL_SHELL_ENABLED } from "../shared/daedalus/kernelShell";
import { GOVERNANCE_KERNEL_ENABLED, KERNEL_IDLE } from "../shared/daedalus/governanceKernel";
import { INVARIANT_REPORT_CLEAN } from "../shared/daedalus/kernelInvariants";
import { HALO_IDLE } from "../shared/daedalus/kernelHalo";
import { CROWN_IDLE } from "../shared/daedalus/kernelCrown";
import { THRONE_IDLE } from "../shared/daedalus/kernelThrone";
import { computeShellState } from "../shared/daedalus/kernelShellEngine";
import { computeHaloSnapshot } from "../shared/daedalus/kernelHaloEngine";
import { computeCrownState } from "../shared/daedalus/kernelCrownEngine";
import { computeThroneView } from "../shared/daedalus/kernelThroneEngine";

export interface KernelShellResult {
  halo: KernelHaloSnapshot;
  crown: CrownState;
  throne: ThroneView;
  rollback: () => void;
}

const BYPASS: KernelShellState = {
  shellStatus: "nominal",
  kernel: KERNEL_IDLE,
  invariants: INVARIANT_REPORT_CLEAN,
};

/**
 * Kernel Shell hook — the outermost governance boundary.
 *
 * Computes the full governance view chain:
 *   shell → halo → crown → throne
 *
 * Returns:
 * - `halo`     — frozen diagnostic snapshot
 * - `crown`    — frozen expressive identity
 * - `throne`   — frozen unified cockpit view (halo + crown merged)
 * - `rollback` — master rollback callback
 */
export function useKernelShell(
  effectiveTuning: AdaptationTuning,
  dashboard: FabricDashboard,
  clearAllFn: () => void,
  rejectAllPendingFn: () => void,
): KernelShellResult {
  const shell = useMemo((): KernelShellState => {
    if (!GOVERNANCE_KERNEL_ENABLED || !KERNEL_SHELL_ENABLED) return BYPASS;
    return computeShellState(effectiveTuning, dashboard);
  }, [effectiveTuning, dashboard]);

  const halo = useMemo((): KernelHaloSnapshot => {
    if (!GOVERNANCE_KERNEL_ENABLED || !KERNEL_SHELL_ENABLED) return HALO_IDLE;
    return computeHaloSnapshot(shell);
  }, [shell]);

  const crown = useMemo((): CrownState => {
    if (!GOVERNANCE_KERNEL_ENABLED || !KERNEL_SHELL_ENABLED) return CROWN_IDLE;
    return computeCrownState(halo);
  }, [halo]);

  const throne = useMemo((): ThroneView => {
    if (!GOVERNANCE_KERNEL_ENABLED || !KERNEL_SHELL_ENABLED) return THRONE_IDLE;
    return computeThroneView(halo, crown);
  }, [halo, crown]);

  const rollback = useCallback(() => {
    rejectAllPendingFn();
    clearAllFn();
  }, [clearAllFn, rejectAllPendingFn]);

  return { halo, crown, throne, rollback };
}
