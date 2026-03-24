import { useMemo, useRef } from "react";
import type { ConductorOutput } from "../shared/daedalus/conductor";
import type { TimelineSnapshot } from "../shared/daedalus/timeline";
import type { OperatorAffectState } from "../shared/daedalus/operatorAffect";
import type { NarrativeOutput, NarrativeConfig } from "../shared/daedalus/narrative";
import { NARRATIVE_SILENT, NARRATIVE_DEFAULTS } from "../shared/daedalus/narrative";
import { generateNarrative } from "../shared/daedalus/narrativeEngine";

/**
 * Produces a narrative line from the current expressive state.
 * Rate-limited: returns null between spoken lines.
 */
export function useNarrative(
  conductor: ConductorOutput,
  timeline: TimelineSnapshot,
  affect: OperatorAffectState,
  config: NarrativeConfig = NARRATIVE_DEFAULTS,
): NarrativeOutput {
  const lastSpokenRef = useRef(0);

  return useMemo(() => {
    const now = Date.now();
    const result = generateNarrative(
      {
        posture: conductor.posture,
        conductorTone: conductor.tone,
        affect,
        timelinePhase: timeline.phase,
        momentum: timeline.momentum,
        continuityBadgeLabel: conductor.continuityBadge?.label ?? null,
      },
      lastSpokenRef.current,
      config,
      now,
    );

    if (result.line !== null) {
      lastSpokenRef.current = now;
    }

    return result;
  }, [conductor, timeline, affect, config]);
}
