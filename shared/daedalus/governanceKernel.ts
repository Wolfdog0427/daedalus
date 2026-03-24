/** Feature toggle: set to false to disable the governance kernel. */
export const GOVERNANCE_KERNEL_ENABLED = true;

/**
 * The three kernel states:
 * - "clean"    — no autonomy overrides active, system at defaults
 * - "tuned"    — one or more tiers have applied governance overrides
 * - "escalated" — tier escalation detected or governance health is overloaded
 */
export type KernelStatus = "clean" | "tuned" | "escalated";

/**
 * The irreducible governance state — the single authoritative view
 * over the entire autonomy stack.
 */
export interface KernelState {
  status: KernelStatus;
  overrideCount: number;
  activeOverrides: string[];
  activeTierCount: number;
  pendingCount: number;
  cappingApplied: boolean;
}

export const KERNEL_IDLE: KernelState = {
  status: "clean",
  overrideCount: 0,
  activeOverrides: [],
  activeTierCount: 0,
  pendingCount: 0,
  cappingApplied: false,
};
