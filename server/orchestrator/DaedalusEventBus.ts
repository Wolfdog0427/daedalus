import type { PostureState, BeingVote, BeingPresenceDetail } from "../../shared/daedalus/contracts";

export type DaedalusEventType =
  | "NODE_GLOW_UPDATED"
  | "NODE_RISK_UPDATED"
  | "NEGOTIATION_COMPLETED"
  | "POSTURE_CHANGED"
  | "GOVERNANCE_OVERRIDE_APPLIED"
  | "CONTINUITY_DRIFT_DETECTED"
  | "BEING_PRESENCE_UPDATED";

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
}

type Listener = (event: DaedalusEventPayload) => void;

export class DaedalusEventBus {
  private listeners: Set<Listener> = new Set();

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  publish(event: DaedalusEventPayload): void {
    for (const listener of this.listeners) {
      try {
        listener(event);
      } catch {
        // Swallow to avoid poisoning the bus.
      }
    }
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
