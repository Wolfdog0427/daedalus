import { useMemo, useRef } from "react";
import type { BeingPresenceDetail } from "../shared/daedalus/contracts";
import { narrateContinuity } from "../shared/daedalus/continuityNarrator";
import type { ContinuitySignal } from "../shared/daedalus/continuityNarrator";

export function useContinuitySignals(
  beings: Record<string, BeingPresenceDetail>,
): ContinuitySignal[] {
  const prevHealthRef = useRef<Record<string, boolean>>({});

  return useMemo(() => {
    const result = narrateContinuity(beings, prevHealthRef.current);

    const healthMap: Record<string, boolean> = {};
    for (const b of Object.values(beings)) {
      healthMap[b.id] = b.continuity.healthy;
    }
    prevHealthRef.current = healthMap;

    return result;
  }, [beings]);
}
