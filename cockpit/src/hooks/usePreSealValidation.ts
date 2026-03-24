import { useMemo } from "react";
import type { PreSealReport } from "../shared/daedalus/preSealValidation";
import { PRE_SEAL_IDLE } from "../shared/daedalus/preSealValidation";
import type { PreSealInput } from "../shared/daedalus/preSealValidationEngine";
import { computePreSealReport } from "../shared/daedalus/preSealValidationEngine";

/**
 * Computes the pre-seal validation report from all integration
 * layer snapshots. Returns PRE_SEAL_IDLE when the shell has not
 * yet produced a non-zero invariant count (system still booting).
 */
export function usePreSealValidation(input: PreSealInput): PreSealReport {
  return useMemo((): PreSealReport => {
    if (input.throne.invariantsTotal === 0) return PRE_SEAL_IDLE;
    return computePreSealReport(input);
  }, [
    input.throne.shellStatus,
    input.throne.invariantsPassed,
    input.throne.invariantsHeld,
    input.throne.invariantsTotal,
    input.throne.kernelStatus,
    input.connectivity.totalCount,
    input.epistemic.freshness,
    input.epistemic.unverifiedWarning,
    input.epistemic.unverifiedCount,
    input.operator.sovereignty,
    input.nodePresence.totalCount,
    input.continuity.health,
    input.continuity.composite,
  ]);
}
