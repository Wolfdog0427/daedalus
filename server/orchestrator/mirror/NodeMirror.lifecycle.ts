import type {
  NodeMirror,
  NodeLifecycleState,
  NodeHeartbeatPayload,
  NodeJoinPayload,
} from "./NodeMirror.types";
import { IDLE_LIFECYCLE, IDLE_EXPRESSIVE } from "./NodeMirror.types";
import type { NodeStatus } from "../../../shared/daedalus/contracts";
import { CANONICAL_OPERATOR_ID } from "../../../shared/daedalus/identity";

const nowIso = () => new Date().toISOString();

type LifecyclePhase = NodeLifecycleState["phase"];

const PHASE_TRANSITIONS: Record<LifecyclePhase, readonly LifecyclePhase[]> = {
  discovered: ["joining"],
  joining: ["negotiating", "detached"],
  negotiating: ["syncing", "detached"],
  syncing: ["active", "detached"],
  active: ["degraded", "quarantined", "detached"],
  degraded: ["active", "quarantined", "detached"],
  quarantined: ["detached"],
  detached: [],
};

export function canTransitionPhase(from: LifecyclePhase, to: LifecyclePhase): boolean {
  return PHASE_TRANSITIONS[from]?.includes(to) ?? false;
}

export function transitionPhase(
  lifecycle: NodeLifecycleState,
  to: LifecyclePhase,
): NodeLifecycleState {
  if (!canTransitionPhase(lifecycle.phase, to)) {
    throw new Error(`Invalid phase transition: ${lifecycle.phase} → ${to}`);
  }
  return { ...lifecycle, phase: to };
}

export function phaseToStatus(phase: LifecyclePhase): NodeStatus {
  switch (phase) {
    case "discovered":
    case "joining":
    case "negotiating":
    case "syncing":
      return "pending";
    case "active":
      return "trusted";
    case "degraded":
      return "pending";
    case "quarantined":
      return "quarantined";
    case "detached":
      return "unknown";
  }
}

export function processJoin(
  mirror: NodeMirror,
  payload: NodeJoinPayload,
): NodeMirror {
  let lifecycle = transitionPhase(mirror.lifecycle, "joining");
  lifecycle = transitionPhase(lifecycle, "negotiating");
  lifecycle = transitionPhase(lifecycle, "syncing");
  lifecycle = {
    ...lifecycle,
    joinedAt: nowIso(),
    lastCapSync: nowIso(),
    lastExpressiveSync: nowIso(),
    lastProfileSync: nowIso(),
  };
  lifecycle = transitionPhase(lifecycle, "active");

  return {
    ...mirror,
    name: payload.name,
    status: phaseToStatus(lifecycle.phase),
    profile: payload.profile,
    capabilities: { entries: [...payload.capabilities] },
    expressive: { ...payload.expressive },
    lifecycle,
  };
}

export function processHeartbeat(
  mirror: NodeMirror,
  payload: NodeHeartbeatPayload,
): NodeMirror {
  const isDegraded = payload.status === "degraded";
  let lifecycle = mirror.lifecycle;

  if (isDegraded && lifecycle.phase === "active") {
    lifecycle = transitionPhase(lifecycle, "degraded");
  } else if (!isDegraded && lifecycle.phase === "degraded") {
    lifecycle = transitionPhase(lifecycle, "active");
  }

  lifecycle = {
    ...lifecycle,
    lastHeartbeat: payload.timestamp,
    heartbeatCount: lifecycle.heartbeatCount + 1,
  };

  return {
    ...mirror,
    status: phaseToStatus(lifecycle.phase),
    lifecycle,
  };
}

export function processError(mirror: NodeMirror, error: string): NodeMirror {
  return {
    ...mirror,
    lifecycle: {
      ...mirror.lifecycle,
      errorCount: mirror.lifecycle.errorCount + 1,
      lastError: error,
    },
  };
}

export function processQuarantine(mirror: NodeMirror): NodeMirror {
  const lifecycle = transitionPhase(mirror.lifecycle, "quarantined");
  return {
    ...mirror,
    status: "quarantined",
    risk: "high",
    lifecycle,
  };
}

export function processDetach(mirror: NodeMirror): NodeMirror {
  const lifecycle = transitionPhase(mirror.lifecycle, "detached");
  return {
    ...mirror,
    status: "unknown",
    lifecycle,
  };
}

export function createFreshMirror(id: string): NodeMirror {
  return {
    id,
    name: id,
    status: "unknown",
    risk: "medium",
    capabilities: { entries: [] },
    profile: {
      id,
      name: id,
      kind: "mobile",
      model: "",
      os: "",
      osVersion: "",
      operatorId: CANONICAL_OPERATOR_ID,
    },
    expressive: { ...IDLE_EXPRESSIVE },
    lifecycle: { ...IDLE_LIFECYCLE },
  };
}
