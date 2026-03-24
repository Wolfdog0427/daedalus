import type { ConductorOutput, ConductorTone } from "./conductor";
import type { NarrativeOutput } from "./narrative";
import type { TimelinePhase } from "./timeline";
import type { OperatorAffectState } from "./operatorAffect";
import type { FusionScene, FusionSceneName } from "./fusion";
import { FUSION_ENABLED, FUSION_SCENE_IDLE } from "./fusion";

export interface FusionInputs {
  conductor: ConductorOutput;
  narrative: NarrativeOutput;
  timelinePhase: TimelinePhase;
  affect: OperatorAffectState;
}

/**
 * Derives a human-readable scene name from the current expressive state.
 *
 * Priority:
 *   1. Timeline phase (temporal arc)
 *   2. Conductor mode (escalated/celebrating)
 *   3. Operator affect (focused/exploratory)
 *   4. Fallback → idle
 */
function deriveSceneName(inputs: FusionInputs): FusionSceneName {
  const { timelinePhase, conductor, affect } = inputs;

  if (timelinePhase === "peak") return "apex";
  if (timelinePhase === "rising") return "rising";
  if (timelinePhase === "cooldown") return "waning";
  if (timelinePhase === "settling") return "settling";

  if (conductor.mode === "escalated") return "alert";
  if (conductor.mode === "celebrating") return "celebrating";

  if (affect === "focused") return "focus";
  if (affect === "exploratory") return "exploring";

  return "idle";
}

/**
 * Resolves the effective tone. The narrative tone takes precedence when
 * the narrative is actively speaking, because it reflects the most
 * specific, immediate expressive moment.
 */
function resolveTone(conductor: ConductorOutput, narrative: NarrativeOutput): ConductorTone {
  if (narrative.line !== null) return narrative.tone;
  return conductor.tone;
}

/**
 * Fuses all expressive channels into a single coherent scene descriptor.
 */
export function computeFusionScene(inputs: FusionInputs): FusionScene {
  if (!FUSION_ENABLED) return FUSION_SCENE_IDLE;

  const { conductor, narrative } = inputs;

  return {
    sceneName: deriveSceneName(inputs),
    mode: conductor.mode,
    tone: resolveTone(conductor, narrative),
    posture: conductor.posture,
    glow: conductor.glowIntensity,
    motion: conductor.motionIntensity,
    suppressAmbientPulse: conductor.suppressAmbientPulse,
    continuityBadge: conductor.continuityBadge,
    narrativeLine: narrative.line,
  };
}
