import { useEffect, useRef } from "react";
import { useDaedalusEventsContext } from "../contexts/DaedalusEventsContext";

export type { DaedalusEventPayload } from "../contexts/DaedalusEventsContext";

// Re-export the type for backward compat
export type DaedalusEventType = string;

export function useDaedalusEvents(onEvent?: (event: any) => void) {
  const ctx = useDaedalusEventsContext();
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;

  useEffect(() => {
    if (!callbackRef.current) return;
    const cb = (event: any) => callbackRef.current?.(event);
    return ctx.subscribe(cb);
  }, [ctx.subscribe]);

  return { lastEvent: ctx.lastEvent, connected: ctx.connected };
}
