/**
 * Connectivity Mirror — a read-only view of network topology,
 * node trust boundaries, and connection health.
 *
 * Derived from existing NodePresence data + SSE state.
 * Feeds into the Throne for display but never into governance logic.
 */

export type SuggestedTrustTier = "low" | "medium" | "high";

export interface ConnectivityNode {
  readonly id: string;
  readonly trusted: boolean;
  readonly quarantined: boolean;
  readonly health: number;
  readonly capabilityCount: number;
  readonly capabilities: readonly string[];
  readonly hasHeartbeat: boolean;
  readonly joinRequested: boolean;
  readonly suggestedTrustTier: SuggestedTrustTier;
}

export interface ConnectivitySnapshot {
  readonly nodes: readonly ConnectivityNode[];
  readonly totalCount: number;
  readonly trustedCount: number;
  readonly quarantinedCount: number;
  readonly pendingJoinCount: number;
  readonly networkQuality: number;
  readonly sseConnected: boolean;
}

export const CONNECTIVITY_IDLE: ConnectivitySnapshot = Object.freeze({
  nodes: Object.freeze([]) as readonly ConnectivityNode[],
  totalCount: 0,
  trustedCount: 0,
  quarantinedCount: 0,
  pendingJoinCount: 0,
  networkQuality: 1,
  sseConnected: false,
});
