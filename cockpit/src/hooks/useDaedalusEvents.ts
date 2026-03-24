import { useEffect, useState, useRef } from "react";
import type { PostureState, BeingVote, BeingPresenceDetail } from "../shared/daedalus/contracts";

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

const ALL_EVENT_TYPES: DaedalusEventType[] = [
  "NODE_GLOW_UPDATED",
  "NODE_RISK_UPDATED",
  "NEGOTIATION_COMPLETED",
  "POSTURE_CHANGED",
  "GOVERNANCE_OVERRIDE_APPLIED",
  "CONTINUITY_DRIFT_DETECTED",
  "BEING_PRESENCE_UPDATED",
];

export function useDaedalusEvents(onEvent?: (event: DaedalusEventPayload) => void) {
  const [lastEvent, setLastEvent] = useState<DaedalusEventPayload | null>(null);
  const [connected, setConnected] = useState(false);
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;

  useEffect(() => {
    const es = new EventSource("/daedalus/events");

    es.onopen = () => setConnected(true);

    const handler = (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data) as DaedalusEventPayload;
        setLastEvent(payload);
        callbackRef.current?.(payload);
      } catch {
        // Ignore malformed payloads
      }
    };

    for (const eventType of ALL_EVENT_TYPES) {
      es.addEventListener(eventType, handler);
    }

    es.onerror = () => setConnected(false);

    return () => {
      es.close();
    };
  }, []);

  return { lastEvent, connected };
}
