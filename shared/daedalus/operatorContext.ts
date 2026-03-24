/**
 * Operator Context — a unified read-only view of the operator's
 * current mode, focus, sovereignty state, and continuity within
 * the Kernel ecosystem.
 *
 * Derived from existing operator affect, intent, panel focus,
 * and override state. Feeds into the Throne for display but
 * never into governance logic.
 */

export type OperatorMode = "focus" | "explore" | "review" | "override";

export interface OperatorContextSnapshot {
  readonly mode: OperatorMode;
  readonly focus: string | null;
  readonly intent: string | null;
  readonly affect: string;

  readonly affectPinned: boolean;
  readonly postureNudged: boolean;
  readonly governorOverridden: boolean;
  readonly overrideCount: number;
  readonly pendingProposals: number;

  readonly sovereignty: number;
}

export const OPERATOR_CONTEXT_IDLE: OperatorContextSnapshot = Object.freeze({
  mode: "focus" as const,
  focus: null,
  intent: null,
  affect: "settled",

  affectPinned: false,
  postureNudged: false,
  governorOverridden: false,
  overrideCount: 0,
  pendingProposals: 0,

  sovereignty: 1,
});
