/**
 * Daedalus Node types — local type definitions that extend or
 * specialize the shared contracts for node-specific behavior.
 */

export interface NodeRuntimeConfig {
  nodeId: string;
  orchestratorUrl: string;
  capabilities: string[];
  heartbeatIntervalMs: number;
}

export interface NodeHeartbeatPayload {
  nodeId: string;
  capabilities: string[];
  uptimeMs: number;
}
