import type { GlowLevel, GlowState, DaedalusPosture, AttentionState, ContinuityState } from "../../../shared/daedalus/contracts";
import type { NodeMirror, ExpressiveState, ExpressiveDelta, NodeExpressiveSyncPayload } from "./NodeMirror.types";

export function computeExpressiveDeltas(
  current: ExpressiveState,
  incoming: ExpressiveState,
): ExpressiveDelta[] {
  const deltas: ExpressiveDelta[] = [];

  if (current.glow.level !== incoming.glow.level || current.glow.intensity !== incoming.glow.intensity) {
    deltas.push({ field: "glow", from: current.glow, to: incoming.glow });
  }
  if (current.posture !== incoming.posture) {
    deltas.push({ field: "posture", from: current.posture, to: incoming.posture });
  }
  if (current.attention.level !== incoming.attention.level) {
    deltas.push({ field: "attention", from: current.attention, to: incoming.attention });
  }
  if (current.continuity.healthy !== incoming.continuity.healthy ||
      current.continuity.streak !== incoming.continuity.streak) {
    deltas.push({ field: "continuity", from: current.continuity, to: incoming.continuity });
  }

  return deltas;
}

export function deriveGlowFromPhase(
  phase: string,
  currentGlow: GlowState,
): GlowState {
  switch (phase) {
    case "active":
      return { level: "high", intensity: Math.max(currentGlow.intensity, 0.7) };
    case "degraded":
      return { level: "low", intensity: Math.min(currentGlow.intensity, 0.3) };
    case "quarantined":
      return { level: "none", intensity: 0 };
    default:
      return currentGlow;
  }
}

export function derivePostureFromPhase(phase: string): DaedalusPosture {
  switch (phase) {
    case "active": return "companion";
    case "degraded": return "observer";
    case "quarantined": return "dormant";
    case "joining":
    case "negotiating":
    case "syncing":
      return "observer";
    default: return "dormant";
  }
}

export function processExpressiveSync(
  mirror: NodeMirror,
  payload: NodeExpressiveSyncPayload,
): { mirror: NodeMirror; deltas: ExpressiveDelta[] } {
  const deltas = computeExpressiveDeltas(mirror.expressive, payload.expressive);

  return {
    mirror: {
      ...mirror,
      expressive: { ...payload.expressive },
      lifecycle: { ...mirror.lifecycle, lastExpressiveSync: payload.timestamp },
    },
    deltas,
  };
}

export function refreshExpressiveFromPhase(mirror: NodeMirror): NodeMirror {
  const phase = mirror.lifecycle.phase;
  return {
    ...mirror,
    expressive: {
      ...mirror.expressive,
      glow: deriveGlowFromPhase(phase, mirror.expressive.glow),
      posture: derivePostureFromPhase(phase),
    },
  };
}
