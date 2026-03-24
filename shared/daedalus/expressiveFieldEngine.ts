import type {
  BeingPresenceDetail,
  BehavioralField,
  DaedalusPosture,
  GlowState,
  AttentionState,
  ContinuityState,
  ExpressiveField,
} from "./contracts";

function clamp(v: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, v));
}

function pickDominant(
  beings: Record<string, BeingPresenceDetail>,
  behavioral: BehavioralField,
): BeingPresenceDetail | null {
  if (!behavioral.dominantBeingId) return null;
  return beings[behavioral.dominantBeingId] ?? null;
}

function deriveArousal(behavioral: BehavioralField): number {
  if (behavioral.signals.length === 0) return 0;
  const highEnergy = behavioral.signals.filter(
    (s) => s.guidanceCue === "strong" || s.avatarMicroMotion === "pulse",
  );
  const base = highEnergy.length > 0 ? 0.6 : 0.3;
  const maxWeight = Math.max(...behavioral.signals.map((s) => s.influenceWeight));
  return clamp(base + maxWeight * 0.4);
}

function deriveFocus(behavioral: BehavioralField): number {
  if (behavioral.signals.length === 0) return 0;
  const dominant = behavioral.signals.find(
    (s) => s.beingId === behavioral.dominantBeingId,
  );
  if (!dominant) return 0.5;
  return clamp(0.4 + dominant.influenceWeight * 0.6);
}

function deriveStability(beings: Record<string, BeingPresenceDetail>): number {
  const list = Object.values(beings);
  if (list.length === 0) return 1;
  const healthyCount = list.filter((b) => b.continuity.healthy).length;
  return clamp(healthyCount / list.length);
}

export interface ExpressiveFieldDefaults {
  fallbackPosture: DaedalusPosture;
  defaultGlow: GlowState;
  defaultAttention: AttentionState;
  defaultContinuity: ContinuityState;
}

export const EXPRESSIVE_DEFAULTS: ExpressiveFieldDefaults = {
  fallbackPosture: "observer",
  defaultGlow: { level: "low", intensity: 0.3 },
  defaultAttention: { level: "unfocused" },
  defaultContinuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: true },
};

export function computeExpressiveField(
  beings: Record<string, BeingPresenceDetail>,
  behavioral: BehavioralField,
  defaults: ExpressiveFieldDefaults = EXPRESSIVE_DEFAULTS,
): ExpressiveField {
  const dominant = pickDominant(beings, behavioral);

  const posture: DaedalusPosture = dominant?.posture ?? defaults.fallbackPosture;
  const glow: GlowState = dominant?.glow ?? defaults.defaultGlow;
  const attention: AttentionState = dominant?.attention ?? defaults.defaultAttention;

  const list = Object.values(beings);
  const continuity: ContinuityState = list.length > 0
    ? list.reduce((best, b) => (b.continuity.streak > best.continuity.streak ? b : best)).continuity
    : defaults.defaultContinuity;

  return {
    posture,
    glow,
    attention,
    continuity,
    behavioral,
    arousal: deriveArousal(behavioral),
    focus: deriveFocus(behavioral),
    stability: deriveStability(beings),
    updatedAt: Date.now(),
  };
}
