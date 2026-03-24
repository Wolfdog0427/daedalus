import { useMemo, useCallback } from "react";
import type { AutonomyDecision } from "../shared/daedalus/sceneAutonomy";
import type { GovernanceFabricSnapshot } from "../shared/daedalus/postAutonomy";
import type { FabricDashboard } from "../shared/daedalus/governanceFabric";
import {
  GOVERNANCE_FABRIC_ENABLED,
  FABRIC_DASHBOARD_IDLE,
} from "../shared/daedalus/governanceFabric";
import { buildDashboard } from "../shared/daedalus/governanceFabricEngine";

export interface GovernanceFabricResult {
  dashboard: FabricDashboard;
  clearAll: () => void;
}

/**
 * Unified Governance Fabric hook.
 *
 * Aggregates the post-autonomy fabric snapshot with cross-tier
 * decision history to produce a single dashboard for the operator.
 * Provides a master `clearAll` that resets every tier's approved tuning.
 */
export function useGovernanceFabric(
  postAutonomyFabric: GovernanceFabricSnapshot,
  allDecisions: AutonomyDecision[],
  pendingCount: number,
  clearFns: (() => void)[],
): GovernanceFabricResult {
  const dashboard = useMemo(() => {
    if (!GOVERNANCE_FABRIC_ENABLED) return FABRIC_DASHBOARD_IDLE;
    return buildDashboard(postAutonomyFabric, allDecisions, pendingCount);
  }, [postAutonomyFabric, allDecisions, pendingCount]);

  const clearAll = useCallback(() => {
    for (const fn of clearFns) fn();
  }, [clearFns]);

  return { dashboard, clearAll };
}
