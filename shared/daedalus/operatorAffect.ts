import type { OrchestrationState } from "./orchestration";

export type OperatorAffectState = "settled" | "focused" | "exploratory" | "under-load";

export interface OperatorAffect {
  /** Operator-pinned state (highest priority). null = no pin. */
  pinned: OperatorAffectState | null;
  /** System-suggested state (lower priority, never forced). */
  suggested: OperatorAffectState;
  /** Effective state: pinned wins, then suggested. */
  effective: OperatorAffectState;
  updatedAt: number;
}

export const OPERATOR_AFFECT_DEFAULTS: OperatorAffect = {
  pinned: null,
  suggested: "settled",
  effective: "settled",
  updatedAt: 0,
};

/** Feature toggle: set to false to suppress affect entirely. */
export const AFFECT_ENABLED = true;

export interface AffectSuggestionInput {
  orchestrationIntent: OrchestrationState["intent"];
  governancePosture: "OPEN" | "ATTENTIVE" | "GUARDED" | "LOCKDOWN";
  panelSwitchCount: number;
  panelStableSince: number;
  now: number;
}
