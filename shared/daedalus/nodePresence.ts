/**
 * Node-Scoped Expressive Presence — per-node identity, heartbeat,
 * glow, capability ribbons, and join-request state.
 *
 * Feeds into the Throne for display but never into governance logic.
 */

import type { SuggestedTrustTier } from "./connectivity";

export interface NodePresenceEntry {
  readonly id: string;
  readonly glow: number;
  readonly heartbeat: number;
  readonly health: number;
  readonly continuity: number;
  readonly trusted: boolean;
  readonly joinRequested: boolean;
  readonly suggestedTrustTier: SuggestedTrustTier;
  readonly capabilityRibbon: string;
}

export interface NodePresenceSnapshot {
  readonly entries: readonly NodePresenceEntry[];
  readonly totalCount: number;
  readonly pendingJoinCount: number;
  readonly joinPulse: number;
}

export const NODE_PRESENCE_IDLE: NodePresenceSnapshot = Object.freeze({
  entries: Object.freeze([]) as readonly NodePresenceEntry[],
  totalCount: 0,
  pendingJoinCount: 0,
  joinPulse: 0,
});
