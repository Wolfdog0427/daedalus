/**
 * Kernel Crown — the expressive, symbolic identity of the Kernel.
 *
 * A read-only surface derived from the KernelHaloSnapshot that
 * gives the operator an at-a-glance feel for governance state.
 * The crown never feeds back into governance logic.
 */

/**
 * Symbolic labels for the crown's visual identity:
 * - "serene"    — clean, nominal, no pending proposals
 * - "attentive" — tuned, governance is actively shaping the system
 * - "vigilant"  — escalated or proposals awaiting approval
 * - "shielded"  — shell is degraded, safe fallback is active
 */
export type CrownSymbol = "serene" | "attentive" | "vigilant" | "shielded";

export interface CrownState {
  readonly symbol: CrownSymbol;
  readonly glow: number;
  readonly pulse: number;
  readonly stability: number;
}

export const CROWN_IDLE: CrownState = Object.freeze({
  symbol: "serene" as const,
  glow: 0.3,
  pulse: 0,
  stability: 1,
});
