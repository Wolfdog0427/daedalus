/**
 * Daedalus shared domain types — canonical contracts consumed by
 * orchestrator, node, kernel, and cockpit.
 *
 * These mirror the authoritative definitions in orchestrator/src/shared/types.ts.
 * When the orchestrator types evolve, update these re-exports to stay aligned.
 */

// ── Node registry ──

export interface NodeDescriptor {
  id: string;
  capabilities: string[];
  lastHeartbeat: string;
  registeredAt: string;
  meta?: Record<string, any>;
}

export interface NodeRegistrySnapshot {
  nodes: Record<string, NodeDescriptor>;
  count: number;
}

// ── Risk & verification ──

export type RiskTier = 'low' | 'medium' | 'elevated' | 'critical';
export type VerificationRequirement = 'none' | 'soft' | 'strong';

export interface VerificationEvent {
  timestamp: string;
  method: string;
  actor: string;
}

export interface RiskSnapshot {
  tier: RiskTier;
  assessedAt: string;
  factors: string[];
}

export interface VerificationSnapshot {
  requirement: VerificationRequirement;
  lastEvent: VerificationEvent | null;
}

// ── Continuity timeline ──

export interface TimelineEntry {
  timestamp: string;
  type: string;
  threadId?: string;
  summary?: string;
  postureAtTime?: string;
}

export interface ContinuityTimelineSnapshot {
  entries: TimelineEntry[];
  threadIds: string[];
}
