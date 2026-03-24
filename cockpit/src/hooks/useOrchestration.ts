import { useRef, useMemo } from "react";
import type { ExpressiveField } from "../shared/daedalus/contracts";
import type { OrchestrationState } from "../shared/daedalus/orchestration";
import { ORCHESTRATION_DEFAULTS } from "../shared/daedalus/orchestration";
import { computeOrchestrationState } from "../shared/daedalus/orchestrationEngine";

export function useOrchestration(field: ExpressiveField): OrchestrationState {
  const prevRef = useRef<OrchestrationState>(ORCHESTRATION_DEFAULTS);

  return useMemo(() => {
    const next = computeOrchestrationState(field, prevRef.current);
    prevRef.current = next;
    return next;
  }, [field]);
}
