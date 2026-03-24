import { useMemo, useRef } from "react";
import type { ConductorOutput } from "../shared/daedalus/conductor";
import { makeInitialGovernorState, GOVERNOR_PRESETS } from "../shared/daedalus/governor";
import type { GovernorState, GovernorConfig, GovernorDisplayInfo } from "../shared/daedalus/governor";
import { governOutput, computeGovernorDisplay } from "../shared/daedalus/governorEngine";

export interface GovernorResult {
  output: ConductorOutput;
  display: GovernorDisplayInfo;
}

/**
 * Wraps the conductor's output with temporal stability.
 * Prevents mode/tone flicker and enforces escalation holds.
 * Accepts runtime config for toggling and preset switching.
 */
export function useGovernor(
  raw: ConductorOutput,
  config: GovernorConfig = GOVERNOR_PRESETS.default,
): GovernorResult {
  const stateRef = useRef<GovernorState | null>(null);

  return useMemo(() => {
    if (!stateRef.current) {
      stateRef.current = makeInitialGovernorState(raw);
    }
    const now = Date.now();
    const { governed, nextState } = governOutput(raw, stateRef.current, now, config);
    stateRef.current = nextState;
    const display = computeGovernorDisplay(nextState, config, now);
    return { output: governed, display };
  }, [raw, config]);
}
