import { useMemo } from "react";
import type { BeingPresenceDetail, ExpressiveField } from "../shared/daedalus/contracts";
import { useBehavioralField } from "./useBehavioralField";
import { computeExpressiveField } from "../shared/daedalus/expressiveFieldEngine";

export function useExpressiveField(
  beings: Record<string, BeingPresenceDetail>,
): ExpressiveField {
  const behavioral = useBehavioralField(beings);
  return useMemo(
    () => computeExpressiveField(beings, behavioral),
    [beings, behavioral],
  );
}
