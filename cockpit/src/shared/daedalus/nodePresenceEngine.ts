import type { ConnectivitySnapshot } from "./connectivity";
import type { NodePresenceEntry, NodePresenceSnapshot } from "./nodePresence";

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, v));
}

/**
 * Derives the expressive glow for a single node from its health,
 * trust status, and join-request state.
 */
export function computeNodeGlow(
  health: number,
  trusted: boolean,
  joinRequested: boolean,
): number {
  if (joinRequested) return clamp(health * 0.4);
  return clamp(health * 0.7 + (trusted ? 0.3 : 0));
}

/**
 * Derives heartbeat intensity. Pending-join nodes pulse strongly
 * to draw operator attention; trusted nodes derive from health.
 */
export function computeNodeHeartbeat(
  health: number,
  joinRequested: boolean,
): number {
  if (joinRequested) return 1;
  return clamp(0.3 + health * 0.5);
}

/**
 * Per-node continuity signal derived from health.
 */
export function computeNodeContinuity(health: number): number {
  return clamp(health * 0.8);
}

/**
 * Builds a single NodePresenceEntry from a ConnectivityNode.
 */
export function mapNodePresenceEntry(
  node: {
    id: string;
    health: number;
    trusted: boolean;
    joinRequested: boolean;
    suggestedTrustTier: "low" | "medium" | "high";
    capabilities: readonly string[];
  },
): NodePresenceEntry {
  return Object.freeze({
    id: node.id,
    glow: computeNodeGlow(node.health, node.trusted, node.joinRequested),
    heartbeat: computeNodeHeartbeat(node.health, node.joinRequested),
    health: node.health,
    continuity: computeNodeContinuity(node.health),
    trusted: node.trusted,
    joinRequested: node.joinRequested,
    suggestedTrustTier: node.suggestedTrustTier,
    capabilityRibbon: node.capabilities.join(" · "),
  });
}

/**
 * Computes the full node presence snapshot from the connectivity
 * layer, including a join-pulse signal (ratio of pending-join nodes).
 */
export function computeNodePresence(
  connectivity: ConnectivitySnapshot,
): NodePresenceSnapshot {
  const entries = connectivity.nodes.map(mapNodePresenceEntry);
  const totalCount = entries.length;
  const pendingJoinCount = entries.filter((e) => e.joinRequested).length;
  const joinPulse = totalCount > 0 ? pendingJoinCount / totalCount : 0;

  return Object.freeze({
    entries: Object.freeze(entries),
    totalCount,
    pendingJoinCount,
    joinPulse,
  });
}
