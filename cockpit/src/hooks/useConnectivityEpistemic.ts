import { useMemo } from "react";
import type { ConnectivitySnapshot } from "../shared/daedalus/connectivity";
import type { EpistemicReport } from "../shared/daedalus/epistemicIntake";
import { CONNECTIVITY_IDLE } from "../shared/daedalus/connectivity";
import { EPISTEMIC_IDLE } from "../shared/daedalus/epistemicIntake";
import { computeConnectivity } from "../shared/daedalus/connectivityEngine";
import type { RawNode } from "../shared/daedalus/connectivityEngine";
import { computeEpistemicReport } from "../shared/daedalus/epistemicIntakeEngine";

export interface ConnectivityEpistemicResult {
  connectivity: ConnectivitySnapshot;
  epistemic: EpistemicReport;
}

/**
 * Computes the connectivity snapshot and epistemic report from
 * the orchestrator's raw node data and SSE connection state.
 *
 * Both outputs are frozen, read-only diagnostics — they feed
 * into the Throne for display but never into governance logic.
 */
export function useConnectivityEpistemic(
  rawNodes: readonly RawNode[],
  sseConnected: boolean,
): ConnectivityEpistemicResult {
  const connectivity = useMemo(
    (): ConnectivitySnapshot => {
      if (rawNodes.length === 0 && !sseConnected) return CONNECTIVITY_IDLE;
      return computeConnectivity(rawNodes, sseConnected);
    },
    [rawNodes, sseConnected],
  );

  const epistemic = useMemo(
    (): EpistemicReport => {
      if (connectivity === CONNECTIVITY_IDLE) return EPISTEMIC_IDLE;
      return computeEpistemicReport(connectivity);
    },
    [connectivity],
  );

  return { connectivity, epistemic };
}
