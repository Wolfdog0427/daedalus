import { useMemo } from "react";
import type { OrchestrationState } from "../shared/daedalus/orchestration";
import type { OperatorAffect } from "../shared/daedalus/operatorAffect";
import type { ContinuitySignal } from "../shared/daedalus/continuityNarrator";
import type { ExpressiveField } from "../shared/daedalus/contracts";
import type { ConductorOutput } from "../shared/daedalus/conductor";
import { computeConductorOutput } from "../shared/daedalus/conductorEngine";

export function useConductor(
  orchestration: OrchestrationState,
  affect: OperatorAffect,
  expressive: ExpressiveField,
  continuitySignals: ContinuitySignal[],
): ConductorOutput {
  return useMemo(
    () =>
      computeConductorOutput({
        orchestrationIntent: orchestration.intent,
        orchestratedPosture: orchestration.orchestratedPosture,
        arousal: orchestration.affect.arousal,
        focus: orchestration.affect.focus,
        stability: orchestration.affect.stability,
        operatorAffect: affect.effective,
        continuitySignals,
        glowIntensity: expressive.glow.intensity,
      }),
    [orchestration, affect.effective, expressive.glow.intensity, continuitySignals],
  );
}
