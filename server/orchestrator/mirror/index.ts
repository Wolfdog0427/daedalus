export type {
  NodeMirror,
  NodeProfile,
  CapabilityMap,
  ExpressiveState,
  NodeLifecycleState,
  NodeHeartbeatPayload,
  NodeJoinPayload,
  NodeCapSyncPayload,
  NodeExpressiveSyncPayload,
  NodeProfileSyncPayload,
  CapabilityDelta,
  ExpressiveDelta,
} from "./NodeMirror.types";

export { IDLE_EXPRESSIVE, IDLE_LIFECYCLE } from "./NodeMirror.types";

export {
  canTransitionPhase,
  transitionPhase,
  phaseToStatus,
  processJoin,
  processHeartbeat,
  processError,
  processQuarantine,
  processDetach,
  createFreshMirror,
} from "./NodeMirror.lifecycle";

export {
  computeCapabilityDeltas,
  negotiateCapabilities,
  validateCapabilities,
  processCapSync,
} from "./NodeMirror.capabilities";

export {
  computeExpressiveDeltas,
  deriveGlowFromPhase,
  derivePostureFromPhase,
  processExpressiveSync,
  refreshExpressiveFromPhase,
} from "./NodeMirror.expressive";

export {
  NodeMirrorRegistry,
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
} from "./NodeMirror";
export type { MirrorEvent } from "./NodeMirror";
