import type {
  BeingPresenceDetail,
  BehavioralSignal,
  BehavioralField,
  AvatarMicroMotion,
  GuidanceCue,
} from "./contracts";

function clamp(v: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, v));
}

function deriveSignal(
  b: BeingPresenceDetail,
  totalInfluence: number,
): BehavioralSignal {
  const weight = totalInfluence > 0 ? b.influenceLevel / totalInfluence : 0;

  const haloIntensity: number =
    b.presenceMode === "dominant"
      ? clamp(0.7 + weight * 0.3)
      : b.presenceMode === "active"
        ? clamp(0.4 + weight * 0.4)
        : b.presenceMode === "ambient"
          ? clamp(0.2 + weight * 0.2)
          : 0.1;

  const haloColorShift: number = b.isSpeaking ? 0.6 : b.isGuiding ? 0.3 : 0;

  const avatarMicroMotion: AvatarMicroMotion = b.isSpeaking
    ? "pulse"
    : b.isGuiding
      ? "lean"
      : b.presenceMode === "active"
        ? "tilt"
        : "none";

  const guidanceCue: GuidanceCue = b.isGuiding
    ? "strong"
    : b.isSpeaking
      ? "subtle"
      : "none";

  return {
    beingId: b.id,
    haloIntensity,
    haloColorShift,
    avatarMicroMotion,
    guidanceCue,
    influenceWeight: weight,
    updatedAt: Date.now(),
  };
}

export function computeBehavioralField(
  beings: Record<string, BeingPresenceDetail>,
): BehavioralField {
  const list = Object.values(beings);
  if (list.length === 0) {
    return { signals: [], dominantBeingId: null, updatedAt: Date.now() };
  }

  const totalInfluence = list.reduce((sum, b) => sum + b.influenceLevel, 0);
  const signals = list.map((b) => deriveSignal(b, totalInfluence));

  const dominant = signals.reduce(
    (top, s) => (s.influenceWeight > top.influenceWeight ? s : top),
    signals[0],
  );

  return {
    signals,
    dominantBeingId: dominant.beingId,
    updatedAt: Date.now(),
  };
}
