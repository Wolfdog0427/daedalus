import type { DaedalusPosture, ExpressiveField } from "./contracts";
import { ORCHESTRATION_DEFAULTS, type OrchestrationState } from "./orchestration";

function clamp(v: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, v));
}

function derivePosture(field: ExpressiveField): DaedalusPosture {
  if (field.stability < 0.3 || field.arousal > 0.7) return "sentinel";

  const dominant = field.behavioral.signals.find(
    (s) => s.beingId === field.behavioral.dominantBeingId,
  );
  if (dominant?.guidanceCue === "strong") return "companion";

  return field.posture;
}

function deriveIntent(field: ExpressiveField): OrchestrationState["intent"] {
  const dominant = field.behavioral.signals.find(
    (s) => s.beingId === field.behavioral.dominantBeingId,
  );

  if (dominant?.guidanceCue === "strong") return "guiding";
  if (field.arousal > 0.7) return "alert";
  if (field.focus > 0.6) return "supporting";
  if (field.stability < 0.4) return "escalating";
  return "idle";
}

function deriveTransition(
  prev: OrchestrationState,
  nextPosture: DaedalusPosture,
  field: ExpressiveField,
): OrchestrationState["transition"] {
  const postureShift: OrchestrationState["transition"]["postureShift"] =
    prev.orchestratedPosture !== nextPosture
      ? field.arousal > 0.6 ? "hard" : "soft"
      : "none";

  return { postureShift, continuityBlend: clamp(field.stability) };
}

export function computeOrchestrationState(
  field: ExpressiveField,
  prev: OrchestrationState = ORCHESTRATION_DEFAULTS,
): OrchestrationState {
  const orchestratedPosture = derivePosture(field);
  const intent = deriveIntent(field);
  const affect = { arousal: field.arousal, focus: field.focus, stability: field.stability };
  const transition = deriveTransition(prev, orchestratedPosture, field);

  return { orchestratedPosture, affect, transition, intent, updatedAt: Date.now() };
}
