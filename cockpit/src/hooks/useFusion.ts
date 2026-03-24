import { useMemo } from "react";
import type { ConductorOutput } from "../shared/daedalus/conductor";
import type { NarrativeOutput } from "../shared/daedalus/narrative";
import type { TimelineSnapshot } from "../shared/daedalus/timeline";
import type { OperatorAffectState } from "../shared/daedalus/operatorAffect";
import type { FusionScene } from "../shared/daedalus/fusion";
import { computeFusionScene } from "../shared/daedalus/fusionEngine";

/**
 * Unifies all expressive channels into a single FusionScene.
 * This is the top of the expressive stack — the UI's primary input.
 */
export function useFusion(
  conductor: ConductorOutput,
  narrative: NarrativeOutput,
  timeline: TimelineSnapshot,
  affect: OperatorAffectState,
): FusionScene {
  return useMemo(
    () =>
      computeFusionScene({
        conductor,
        narrative,
        timelinePhase: timeline.phase,
        affect,
      }),
    [conductor, narrative, timeline.phase, affect],
  );
}
