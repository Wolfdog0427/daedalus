import type {
  Capability,
  GlowLevel,
  GlowState,
  RiskTier,
  NodeStatus,
  DaedalusPosture,
  AttentionState,
  ContinuityState,
} from "../../../shared/daedalus/contracts";

export interface NodeProfile {
  readonly id: string;
  readonly name: string;
  readonly kind: "mobile" | "desktop" | "server" | "embedded";
  readonly model: string;
  readonly os: string;
  readonly osVersion: string;
  readonly operatorId: string;
}

export interface CapabilityMap {
  readonly entries: Capability[];
}

export interface ExpressiveState {
  readonly glow: GlowState;
  readonly posture: DaedalusPosture;
  readonly attention: AttentionState;
  readonly continuity: ContinuityState;
}

export interface NodeLifecycleState {
  readonly phase: "discovered" | "joining" | "negotiating" | "syncing" | "active" | "degraded" | "quarantined" | "detached";
  readonly joinedAt: string | null;
  readonly lastHeartbeat: string | null;
  readonly heartbeatCount: number;
  readonly lastCapSync: string | null;
  readonly lastExpressiveSync: string | null;
  readonly lastProfileSync: string | null;
  readonly errorCount: number;
  readonly lastError: string | null;
}

export interface NodeMirror {
  readonly id: string;
  readonly name: string;
  readonly status: NodeStatus;
  readonly risk: RiskTier;
  readonly capabilities: CapabilityMap;
  readonly profile: NodeProfile;
  readonly expressive: ExpressiveState;
  readonly lifecycle: NodeLifecycleState;
}

export interface NodeHeartbeatPayload {
  readonly nodeId: string;
  readonly timestamp: string;
  readonly status: "alive" | "degraded";
  readonly batteryBand?: string;
  readonly connectivityBand?: string;
  readonly anomalies?: string[];
  readonly load?: Record<string, unknown>;
}

export interface NodeJoinPayload {
  readonly nodeId: string;
  readonly name: string;
  readonly profile: NodeProfile;
  readonly capabilities: Capability[];
  readonly expressive: ExpressiveState;
}

export interface NodeCapSyncPayload {
  readonly nodeId: string;
  readonly capabilities: Capability[];
  readonly timestamp: string;
}

export interface NodeExpressiveSyncPayload {
  readonly nodeId: string;
  readonly expressive: ExpressiveState;
  readonly timestamp: string;
}

export interface NodeProfileSyncPayload {
  readonly nodeId: string;
  readonly profile: NodeProfile;
  readonly timestamp: string;
}

export interface CapabilityDelta {
  readonly name: string;
  readonly from: { enabled: boolean; value: string } | null;
  readonly to: { enabled: boolean; value: string };
}

export interface ExpressiveDelta {
  readonly field: keyof ExpressiveState;
  readonly from: unknown;
  readonly to: unknown;
}

export const IDLE_EXPRESSIVE: ExpressiveState = Object.freeze({
  glow: Object.freeze({ level: "medium" as GlowLevel, intensity: 0.5 }),
  posture: "observer" as DaedalusPosture,
  attention: Object.freeze({ level: "aware" as const }),
  continuity: Object.freeze({ streak: 0, lastCheckIn: "", healthy: true }),
});

export const IDLE_LIFECYCLE: NodeLifecycleState = Object.freeze({
  phase: "discovered" as const,
  joinedAt: null,
  lastHeartbeat: null,
  heartbeatCount: 0,
  lastCapSync: null,
  lastExpressiveSync: null,
  lastProfileSync: null,
  errorCount: 0,
  lastError: null,
});
