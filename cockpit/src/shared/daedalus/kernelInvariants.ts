/**
 * Kernel Invariants — the unbreakable constitutional rules
 * of Daedalus expressive governance.
 *
 * Each invariant is either:
 * - **structural**: guaranteed by the architecture itself (hooks,
 *   pure functions, operator-gated approval). Always passes.
 * - **runtime**: validated against live state every cycle.
 *   A failure indicates a bug, not an operator error.
 */

export type InvariantName =
  | "operator-sovereignty"
  | "no-silent-changes"
  | "single-proposal-bounded"
  | "bounded-overrides"
  | "caps-enforced"
  | "rollback-available"
  | "no-escalation-leak"
  | "deterministic-merge"
  | "no-recursive-governance";

export interface InvariantCheck {
  name: InvariantName;
  passed: boolean;
}

export interface InvariantReport {
  allPassed: boolean;
  checks: InvariantCheck[];
  failedCount: number;
}

export const INVARIANT_REPORT_CLEAN: InvariantReport = {
  allPassed: true,
  checks: [],
  failedCount: 0,
};

/** Maximum number of autonomy tiers that can have pending proposals. */
export const MAX_PENDING_PROPOSALS = 5;

/** Maximum number of tuning fields that can be overridden. */
export const MAX_TUNING_FIELDS = 6;
