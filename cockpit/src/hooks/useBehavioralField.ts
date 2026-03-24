import { useMemo } from "react";
import type { BeingPresenceDetail, BehavioralField } from "../shared/daedalus/contracts";
import { computeBehavioralField } from "../shared/daedalus/behavioralGrammar";

export function useBehavioralField(
  beings: Record<string, BeingPresenceDetail>,
): BehavioralField {
  return useMemo(() => computeBehavioralField(beings), [beings]);
}
