import type { ConductorInputs, ConductorOutput, ConductorMode, ConductorTone, ConductorBadge } from "./conductor";
import { CONDUCTOR_ENABLED, CONDUCTOR_DEFAULTS } from "./conductor";

function clamp(v: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, v));
}

/**
 * Priority model:
 *   1. Orchestration intent (safety & escalation) — highest
 *   2. Operator affect (operator-driven mood) — modulates
 *   3. Continuity signals (narrative flavor) — adds badges when safe
 *
 * The conductor resolves conflicts so layers never contradict each other.
 */
export function computeConductorOutput(inputs: ConductorInputs): ConductorOutput {
  if (!CONDUCTOR_ENABLED) return { ...CONDUCTOR_DEFAULTS, updatedAt: Date.now() };

  const {
    orchestrationIntent,
    orchestratedPosture,
    arousal,
    focus,
    stability,
    operatorAffect,
    continuitySignals,
    glowIntensity: rawGlow,
  } = inputs;

  let mode: ConductorMode;
  let tone: ConductorTone;
  let glowIntensity: number;
  let motionIntensity: number;
  let suppressAmbientPulse = false;
  let continuityBadge: ConductorBadge | null = null;

  // ── Layer 1: Orchestration intent (highest priority) ──────────
  const isEscalated = orchestrationIntent === "alert" || orchestrationIntent === "escalating";

  if (isEscalated) {
    mode = "escalated";
    tone = "alert";
    glowIntensity = clamp(rawGlow * 1.4, 0, 1);
    motionIntensity = clamp(0.7 + arousal * 0.3);
    suppressAmbientPulse = true;
  } else if (orchestrationIntent === "guiding") {
    mode = "attentive";
    tone = "focused";
    glowIntensity = clamp(rawGlow * 1.1);
    motionIntensity = clamp(0.5 + focus * 0.3);
    suppressAmbientPulse = false;
  } else if (orchestrationIntent === "supporting") {
    mode = "attentive";
    tone = "neutral";
    glowIntensity = clamp(rawGlow * 1.05);
    motionIntensity = clamp(0.4 + focus * 0.2);
    suppressAmbientPulse = false;
  } else {
    mode = "resting";
    tone = "neutral";
    glowIntensity = rawGlow;
    motionIntensity = clamp(0.3 + arousal * 0.2);
    suppressAmbientPulse = false;
  }

  // ── Layer 2: Operator affect (modulates) ──────────────────────
  if (operatorAffect === "focused") {
    if (!isEscalated) tone = "focused";
    motionIntensity *= 0.6;
    glowIntensity *= 0.8;
    suppressAmbientPulse = true;
  } else if (operatorAffect === "exploratory") {
    glowIntensity = clamp(glowIntensity * 1.15);
    motionIntensity = clamp(motionIntensity * 1.1);
  } else if (operatorAffect === "under-load") {
    if (!isEscalated) {
      mode = "escalated";
      tone = "alert";
    }
    motionIntensity = clamp(motionIntensity * 1.2);
  }

  // ── Layer 3: Continuity (flavor when safe) ────────────────────
  const threshold = continuitySignals.find((s) => s.kind === "threshold");
  const recovery = continuitySignals.find((s) => s.kind === "drift-recovery");

  if (!isEscalated && operatorAffect !== "under-load") {
    if (threshold) {
      continuityBadge = { kind: "threshold", label: threshold.label };
      if (tone === "neutral") {
        mode = "celebrating";
        tone = "celebratory";
      }
    } else if (recovery) {
      continuityBadge = { kind: "drift-recovery", label: recovery.label };
      if (tone === "neutral") tone = "celebratory";
    }
  }

  return {
    mode,
    tone,
    posture: orchestratedPosture,
    glowIntensity: clamp(glowIntensity),
    motionIntensity: clamp(motionIntensity),
    suppressAmbientPulse,
    continuityBadge,
    updatedAt: Date.now(),
  };
}
