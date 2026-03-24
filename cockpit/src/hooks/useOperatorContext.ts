import { useMemo } from "react";
import type { OperatorContextSnapshot } from "../shared/daedalus/operatorContext";
import { OPERATOR_CONTEXT_IDLE } from "../shared/daedalus/operatorContext";
import {
  computeOperatorContext,
  type OperatorContextInput,
} from "../shared/daedalus/operatorContextEngine";

/**
 * Computes a unified, frozen operator context snapshot from the
 * cockpit's existing operator-related state. Read-only diagnostic.
 */
export function useOperatorContext(input: OperatorContextInput): OperatorContextSnapshot {
  return useMemo((): OperatorContextSnapshot => {
    return computeOperatorContext(input);
  }, [
    input.activePanel,
    input.affectEffective,
    input.affectPinned,
    input.currentIntent,
    input.postureNudge,
    input.governorEnabled,
    input.governorPreset,
    input.pendingProposals,
  ]);
}
