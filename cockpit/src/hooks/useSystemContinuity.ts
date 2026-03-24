import { useMemo } from "react";
import type { SystemContinuitySnapshot } from "../shared/daedalus/systemContinuity";
import { SYSTEM_CONTINUITY_IDLE } from "../shared/daedalus/systemContinuity";
import {
  computeSystemContinuity,
  type SystemContinuityInput,
} from "../shared/daedalus/systemContinuityEngine";

/**
 * Computes a unified, frozen system continuity snapshot from
 * the expressive field, orchestration, embodied presence,
 * continuity signals, timeline, and persistence state.
 * Read-only diagnostic for the Throne.
 */
export function useSystemContinuity(
  input: SystemContinuityInput,
): SystemContinuitySnapshot {
  return useMemo((): SystemContinuitySnapshot => {
    if (input.beingCount === 0 && input.timelineMomentum === 0) {
      return SYSTEM_CONTINUITY_IDLE;
    }
    return computeSystemContinuity(input);
  }, [
    input.beingStability,
    input.beingCount,
    input.bestStreak,
    input.driftSignalCount,
    input.anchorBeingId,
    input.orchestrationStability,
    input.continuityBlend,
    input.embodiedContinuity,
    input.motionGrammar,
    input.timelineMomentum,
    input.persistenceRestored,
  ]);
}
