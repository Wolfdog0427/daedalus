import { useMemo } from "react";
import type { ConnectivitySnapshot } from "../shared/daedalus/connectivity";
import type { NodePresenceSnapshot } from "../shared/daedalus/nodePresence";
import { NODE_PRESENCE_IDLE } from "../shared/daedalus/nodePresence";
import { computeNodePresence } from "../shared/daedalus/nodePresenceEngine";

/**
 * Derives the node-scoped expressive presence snapshot from
 * the connectivity layer. Read-only diagnostic for the Throne.
 */
export function useNodePresence(
  connectivity: ConnectivitySnapshot,
): NodePresenceSnapshot {
  return useMemo((): NodePresenceSnapshot => {
    if (connectivity.totalCount === 0) return NODE_PRESENCE_IDLE;
    return computeNodePresence(connectivity);
  }, [connectivity]);
}
