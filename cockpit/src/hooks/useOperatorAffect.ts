import { useState, useRef, useCallback, useMemo } from "react";
import type { OperatorAffect, OperatorAffectState, AffectSuggestionInput } from "../shared/daedalus/operatorAffect";
import { OPERATOR_AFFECT_DEFAULTS, AFFECT_ENABLED } from "../shared/daedalus/operatorAffect";
import type { OrchestrationState } from "../shared/daedalus/orchestration";
import type { PostureState } from "../shared/daedalus/contracts";
import { suggestAffect, resolveAffect } from "../shared/daedalus/affectEngine";

interface UseOperatorAffectOptions {
  orchestration: OrchestrationState;
  governancePosture: PostureState;
  activePanel: string;
}

export interface OperatorAffectControls {
  affect: OperatorAffect;
  pin: (state: OperatorAffectState) => void;
  unpin: () => void;
}

export function useOperatorAffect({
  orchestration,
  governancePosture,
  activePanel,
}: UseOperatorAffectOptions): OperatorAffectControls {
  const [pinned, setPinned] = useState<OperatorAffectState | null>(null);

  const panelSwitchCountRef = useRef(0);
  const panelStableSinceRef = useRef(Date.now());
  const lastPanelRef = useRef(activePanel);

  if (activePanel !== lastPanelRef.current) {
    lastPanelRef.current = activePanel;
    panelSwitchCountRef.current += 1;
    panelStableSinceRef.current = Date.now();
  }

  const suggested = useMemo((): OperatorAffectState => {
    if (!AFFECT_ENABLED) return "settled";

    const input: AffectSuggestionInput = {
      orchestrationIntent: orchestration.intent,
      governancePosture,
      panelSwitchCount: panelSwitchCountRef.current,
      panelStableSince: panelStableSinceRef.current,
      now: Date.now(),
    };
    return suggestAffect(input);
  }, [orchestration.intent, governancePosture, activePanel]);

  const effective = resolveAffect(pinned, suggested);

  const affect: OperatorAffect = {
    pinned,
    suggested,
    effective,
    updatedAt: Date.now(),
  };

  const pin = useCallback((state: OperatorAffectState) => setPinned(state), []);
  const unpin = useCallback(() => setPinned(null), []);

  return { affect, pin, unpin };
}
