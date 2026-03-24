import type { DaedalusPosture } from "./contracts";
import type { ConductorTone } from "./conductor";
import type { OperatorAffectState } from "./operatorAffect";
import type { TimelinePhase } from "./timeline";

/** Feature toggle: set to false to suppress all narrative output. */
export const NARRATIVE_ENABLED = true;

export interface NarrativeInput {
  posture: DaedalusPosture;
  conductorTone: ConductorTone;
  affect: OperatorAffectState;
  timelinePhase: TimelinePhase;
  momentum: number;
  continuityBadgeLabel: string | null;
}

export interface NarrativeOutput {
  line: string | null;
  tone: ConductorTone;
}

export interface NarrativeConfig {
  minIntervalMs: number;
  momentumThreshold: number;
}

export const NARRATIVE_DEFAULTS: NarrativeConfig = {
  minIntervalMs: 3500,
  momentumThreshold: 0.15,
};

export const NARRATIVE_SILENT: NarrativeOutput = { line: null, tone: "neutral" };
