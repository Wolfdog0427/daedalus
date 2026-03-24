import type { OperatorAffectState, AffectSuggestionInput } from "./operatorAffect";

const FOCUSED_DWELL_MS = 60_000;
const EXPLORATORY_SWITCHES = 3;
const EXPLORATORY_WINDOW_MS = 30_000;
const SETTLED_COOLDOWN_MS = 120_000;

export function suggestAffect(input: AffectSuggestionInput): OperatorAffectState {
  const { orchestrationIntent, governancePosture, panelSwitchCount, panelStableSince, now } = input;

  const isHighStakes =
    (orchestrationIntent === "alert" || orchestrationIntent === "escalating") &&
    (governancePosture === "GUARDED" || governancePosture === "LOCKDOWN");
  if (isHighStakes) return "under-load";

  const dwellMs = now - panelStableSince;
  if (dwellMs > FOCUSED_DWELL_MS) return "focused";

  if (panelSwitchCount >= EXPLORATORY_SWITCHES && dwellMs < EXPLORATORY_WINDOW_MS) {
    return "exploratory";
  }

  return "settled";
}

export function resolveAffect(
  pinned: OperatorAffectState | null,
  suggested: OperatorAffectState,
): OperatorAffectState {
  return pinned ?? suggested;
}

export { FOCUSED_DWELL_MS, EXPLORATORY_SWITCHES, EXPLORATORY_WINDOW_MS, SETTLED_COOLDOWN_MS };
