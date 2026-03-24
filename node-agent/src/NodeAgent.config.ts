import type { Capability, DaedalusPosture, GlowState, AttentionState, ContinuityState } from "../../shared/daedalus/contracts";
import { CANONICAL_OPERATOR_ID } from "../../shared/daedalus/identity";

export interface NodeAgentConfig {
  readonly nodeId: string;
  readonly nodeName: string;
  readonly kind: "mobile" | "desktop" | "server" | "embedded";
  readonly model: string;
  readonly os: string;
  readonly osVersion: string;
  readonly operatorId: string;
  readonly orchestratorUrl: string;
  readonly heartbeatIntervalMs: number;
  readonly expressiveSyncIntervalMs: number;
  readonly capabilities: Capability[];
}

export const DEFAULT_AGENT_CONFIG: NodeAgentConfig = Object.freeze({
  nodeId: "",
  nodeName: "",
  kind: "mobile" as const,
  model: "",
  os: "",
  osVersion: "",
  operatorId: CANONICAL_OPERATOR_ID,
  orchestratorUrl: "http://localhost:3001",
  heartbeatIntervalMs: 4000,
  expressiveSyncIntervalMs: 8000,
  capabilities: [],
});
