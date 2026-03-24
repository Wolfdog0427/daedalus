import { useEffect, useState, useCallback } from "react";
import { fetchBeingPresences } from "../api/daedalusClient";
import { useDaedalusEvents } from "./useDaedalusEvents";
import type { DaedalusEventPayload } from "./useDaedalusEvents";
import type { BeingPresenceDetail } from "../shared/daedalus/contracts";

export function useBeingPresences(): Record<string, BeingPresenceDetail> {
  const [beings, setBeings] = useState<Record<string, BeingPresenceDetail>>({});

  useEffect(() => {
    fetchBeingPresences()
      .then((list) => {
        const map: Record<string, BeingPresenceDetail> = {};
        for (const b of list) map[b.id] = b;
        setBeings(map);
      })
      .catch(() => {});
  }, []);

  useDaedalusEvents(
    useCallback((event: DaedalusEventPayload) => {
      if (event.type === "BEING_PRESENCE_UPDATED" && event.beingId && event.beingPresence) {
        setBeings((prev) => ({ ...prev, [event.beingId!]: event.beingPresence! }));
      }
    }, []),
  );

  return beings;
}
