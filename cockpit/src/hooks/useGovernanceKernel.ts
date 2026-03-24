import { useMemo, useCallback } from "react";
import type { AdaptationTuning } from "../shared/daedalus/sceneAdaptation";
import type { FabricDashboard } from "../shared/daedalus/governanceFabric";
import type { KernelState } from "../shared/daedalus/governanceKernel";
import type { InvariantReport } from "../shared/daedalus/kernelInvariants";
import { GOVERNANCE_KERNEL_ENABLED, KERNEL_IDLE } from "../shared/daedalus/governanceKernel";
import { INVARIANT_REPORT_CLEAN } from "../shared/daedalus/kernelInvariants";
import { computeKernelState } from "../shared/daedalus/governanceKernelEngine";
import { validateInvariants } from "../shared/daedalus/kernelInvariantsEngine";

export interface GovernanceKernelResult {
  kernel: KernelState;
  invariants: InvariantReport;
  rollback: () => void;
}

/**
 * Governance Kernel hook — the apex of the autonomy stack.
 *
 * Computes the authoritative kernel state, validates all
 * invariants against live state, and provides a single
 * rollback that clears all approved tuning AND rejects
 * every pending proposal across all tiers.
 */
export function useGovernanceKernel(
  effectiveTuning: AdaptationTuning,
  dashboard: FabricDashboard,
  clearAllFn: () => void,
  rejectAllPendingFn: () => void,
): GovernanceKernelResult {
  const kernel = useMemo(() => {
    if (!GOVERNANCE_KERNEL_ENABLED) return KERNEL_IDLE;
    return computeKernelState(effectiveTuning, dashboard);
  }, [effectiveTuning, dashboard]);

  const invariants = useMemo(() => {
    if (!GOVERNANCE_KERNEL_ENABLED) return INVARIANT_REPORT_CLEAN;
    return validateInvariants(kernel, dashboard, effectiveTuning);
  }, [kernel, dashboard, effectiveTuning]);

  const rollback = useCallback(() => {
    rejectAllPendingFn();
    clearAllFn();
  }, [clearAllFn, rejectAllPendingFn]);

  return { kernel, invariants, rollback };
}
