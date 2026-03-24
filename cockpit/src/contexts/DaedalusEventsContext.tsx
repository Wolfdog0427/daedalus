import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from "react";

type DaedalusEventType = string;

export interface DaedalusEventPayload {
  type: DaedalusEventType;
  timestamp: string;
  [key: string]: any;
}

type EventCallback = (event: DaedalusEventPayload) => void;

interface DaedalusEventsContextValue {
  lastEvent: DaedalusEventPayload | null;
  connected: boolean;
  subscribe: (callback: EventCallback) => () => void;
}

const DaedalusEventsContext = createContext<DaedalusEventsContextValue>({
  lastEvent: null,
  connected: false,
  subscribe: () => () => {},
});

const ALL_EVENT_TYPES: string[] = [
  "NODE_GLOW_UPDATED",
  "NODE_RISK_UPDATED",
  "NEGOTIATION_COMPLETED",
  "POSTURE_CHANGED",
  "GOVERNANCE_OVERRIDE_APPLIED",
  "CONTINUITY_DRIFT_DETECTED",
  "BEING_PRESENCE_UPDATED",
  "STRATEGY_CHANGED",
  "ALIGNMENT_ESCALATION",
  "SAFE_MODE_ACTIVE",
  "ALIGNMENT_CONFIG_CHANGED",
  "CHANGE_AUTO_APPROVED",
  "CHANGE_REQUIRES_REVIEW",
  "REGULATION_MACRO_FIRED",
  "REGULATION_SAFE_MODE_SIGNAL",
  "CHANGE_REGISTERED",
  "CHANGE_ROLLED_BACK",
  "CHANGE_ACCEPTED",
  "OPERATOR_BOUND",
  "OPERATOR_UNBOUND",
  "OPERATOR_TRUST_SUSPICIOUS",
  "OPERATOR_HIGH_RISK_DENIED",
  "CONSTITUTIONAL_FREEZE_CHANGED",
  "MIRROR_NODE_JOINED",
  "MIRROR_NODE_HEARTBEAT",
  "MIRROR_NODE_QUARANTINED",
  "MIRROR_NODE_DETACHED",
  "MIRROR_NODE_ERROR",
  "MIRROR_NODE_STALE",
  "MIRROR_NODE_CAP_SYNCED",
  "MIRROR_NODE_EXPRESSIVE_SYNCED",
  "MIRROR_NODE_PROFILE_SYNCED",
];

export function DaedalusEventsProvider({ children }: { children: React.ReactNode }) {
  const [lastEvent, setLastEvent] = useState<DaedalusEventPayload | null>(null);
  const [connected, setConnected] = useState(false);
  const subscribersRef = useRef<Set<EventCallback>>(new Set());

  const subscribe = useCallback((callback: EventCallback) => {
    subscribersRef.current.add(callback);
    return () => {
      subscribersRef.current.delete(callback);
    };
  }, []);

  useEffect(() => {
    const token = import.meta.env.VITE_DAEDALUS_TOKEN ?? "daedalus-dev-token";
    const apiBase = import.meta.env.VITE_DAEDALUS_API_BASE || "/daedalus";
    let es: EventSource | null = null;
    let retryDelay = 1000;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      es = new EventSource(`${apiBase}/events?token=${encodeURIComponent(token)}`);

      es.onopen = () => {
        setConnected(true);
        retryDelay = 1000;
      };

      const handler = (e: MessageEvent) => {
        try {
          const payload = JSON.parse(e.data) as DaedalusEventPayload;
          setLastEvent(payload);
          for (const cb of subscribersRef.current) {
            try {
              cb(payload);
            } catch {
              /* subscriber error */
            }
          }
        } catch {
          /* malformed payload */
        }
      };

      for (const eventType of ALL_EVENT_TYPES) {
        es.addEventListener(eventType, handler);
      }

      es.onerror = () => {
        setConnected(false);
        es?.close();
        if (!cancelled) {
          retryTimer = setTimeout(connect, retryDelay);
          retryDelay = Math.min(retryDelay * 2, 30000);
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      es?.close();
    };
  }, []);

  return (
    <DaedalusEventsContext.Provider value={{ lastEvent, connected, subscribe }}>
      {children}
    </DaedalusEventsContext.Provider>
  );
}

export function useDaedalusEventsContext() {
  return useContext(DaedalusEventsContext);
}
