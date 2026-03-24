import { useMemo } from "react";
import type { EmbodiedPresenceSnapshot } from "../shared/daedalus/embodiedPresence";
import { EMBODIED_IDLE } from "../shared/daedalus/embodiedPresence";
import {
  computeEmbodiedPresence,
  type EmbodiedPresenceInput,
} from "../shared/daedalus/embodiedPresenceEngine";

/**
 * Computes a unified, frozen embodied presence snapshot from
 * the expressive field, scene output, and connectivity state.
 * Read-only diagnostic for the Throne.
 */
export function useEmbodiedPresence(
  input: EmbodiedPresenceInput,
): EmbodiedPresenceSnapshot {
  return useMemo((): EmbodiedPresenceSnapshot => {
    if (input.beingCount === 0 && input.connectivityNodes.length === 0) {
      return EMBODIED_IDLE;
    }
    return computeEmbodiedPresence(input);
  }, [
    input.beingCount,
    input.dominantBeingId,
    input.posture,
    input.arousal,
    input.focus,
    input.stability,
    input.sceneGlow,
    input.sceneMotion,
    input.connectivityNodes,
  ]);
}
