import { useMemo } from "react";
import type { AttentionTaskSnapshot } from "../shared/daedalus/attentionTask";
import { ATTENTION_TASK_IDLE } from "../shared/daedalus/attentionTask";
import {
  computeAttentionTask,
  type AttentionTaskInput,
} from "../shared/daedalus/attentionTaskEngine";

/**
 * Computes a unified, frozen attention + task snapshot from the
 * expressive field, orchestration, and operator context.
 * Read-only diagnostic for the Throne.
 */
export function useAttentionTask(
  input: AttentionTaskInput,
): AttentionTaskSnapshot {
  return useMemo((): AttentionTaskSnapshot => {
    if (
      input.expressiveFocus === 0 &&
      input.expressiveArousal === 0 &&
      input.orchestrationIntent === "idle" &&
      input.operatorIntent === null
    ) {
      return ATTENTION_TASK_IDLE;
    }
    return computeAttentionTask(input);
  }, [
    input.expressiveAttentionLevel,
    input.expressiveFocus,
    input.expressiveArousal,
    input.expressiveStability,
    input.orchestrationIntent,
    input.activePanel,
    input.operatorIntent,
    input.pendingProposals,
  ]);
}
