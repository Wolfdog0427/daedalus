import type { PostureState, BeingVote, BeingPresenceDetail } from "../../shared/daedalus/contracts";

export type DaedalusEventType =
  | "NODE_GLOW_UPDATED"
  | "NODE_RISK_UPDATED"
  | "NEGOTIATION_COMPLETED"
  | "POSTURE_CHANGED"
  | "GOVERNANCE_OVERRIDE_APPLIED"
  | "CONTINUITY_DRIFT_DETECTED"
  | "BEING_PRESENCE_UPDATED"
  | "STRATEGY_CHANGED"
  | "ALIGNMENT_ESCALATION"
  | "SAFE_MODE_ACTIVE"
  | "ALIGNMENT_CONFIG_CHANGED"
  | "CHANGE_AUTO_APPROVED"
  | "CHANGE_REQUIRES_REVIEW"
  | "REGULATION_MACRO_FIRED"
  | "REGULATION_SAFE_MODE_SIGNAL"
  | "CHANGE_REGISTERED"
  | "CHANGE_ROLLED_BACK"
  | "CHANGE_ACCEPTED"
  | "OPERATOR_BOUND"
  | "OPERATOR_UNBOUND"
  | "OPERATOR_TRUST_SUSPICIOUS"
  | "OPERATOR_HIGH_RISK_DENIED"
  | "CONSTITUTIONAL_FREEZE_CHANGED"
  | "MIRROR_NODE_JOINED"
  | "MIRROR_NODE_HEARTBEAT"
  | "MIRROR_NODE_QUARANTINED"
  | "MIRROR_NODE_DETACHED"
  | "MIRROR_NODE_ERROR"
  | "MIRROR_NODE_STALE"
  | "MIRROR_NODE_CAP_SYNCED"
  | "MIRROR_NODE_EXPRESSIVE_SYNCED"
  | "MIRROR_NODE_PROFILE_SYNCED";

export interface DaedalusEventPayload {
  type: DaedalusEventType;
  timestamp: string;
  nodeId?: string;
  negotiationId?: string;
  glow?: string;
  risk?: string;
  summary?: string;
  beings?: BeingVote[];
  posture?: PostureState;
  governanceOverrideId?: string;
  continuityDriftId?: string;
  beingId?: string;
  beingPresence?: BeingPresenceDetail;
  mirrorPhase?: string;
  mirrorStatus?: string;
  strategy?: string;
  alignment?: number;
}

type Listener = (event: DaedalusEventPayload) => void;

export class DaedalusEventBus {
  private listeners: Set<Listener> = new Set();
  private history: DaedalusEventPayload[] = [];
  private static readonly MAX_HISTORY = 1000;

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  publish(event: DaedalusEventPayload): void {
    if (this.history.length >= DaedalusEventBus.MAX_HISTORY) {
      this.history.shift();
    }
    this.history.push(event);

    for (const listener of this.listeners) {
      try {
        listener(event);
      } catch {
        // Swallow to avoid poisoning the bus.
      }
    }
  }

  getHistory(limit?: number): DaedalusEventPayload[] {
    if (!limit) return [...this.history];
    return this.history.slice(-limit);
  }

  getHistoryByType(type: DaedalusEventType, limit?: number): DaedalusEventPayload[] {
    const filtered = this.history.filter((e) => e.type === type);
    if (!limit) return filtered;
    return filtered.slice(-limit);
  }

  clearHistory(): void {
    this.history = [];
  }
}

let singleton: DaedalusEventBus | null = null;

export function getDaedalusEventBus(): DaedalusEventBus {
  if (!singleton) {
    singleton = new DaedalusEventBus();
  }
  return singleton;
}

export function resetDaedalusEventBus(): void {
  singleton = null;
}

export function nowIso(): string {
  return new Date().toISOString();
}
