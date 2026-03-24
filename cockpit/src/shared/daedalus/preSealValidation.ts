/**
 * Pre-Seal Validation — a one-shot structural audit of the entire
 * Kernel integration chain.
 *
 * Checks Shell → Halo → Crown → Throne wiring, all integration
 * layers (connectivity, epistemic, operator, embodied, node,
 * attention, continuity), and kernel invariant consistency.
 *
 * Returns a frozen report: issue list, pass/fail, and summary.
 * Feeds into the Throne for display but never into governance logic.
 */

export type PreSealIssueKind =
  | "shell-degraded"
  | "invariant-failure"
  | "orphan-nodes"
  | "epistemic-unverified"
  | "epistemic-stale"
  | "continuity-fragile"
  | "sovereignty-low"
  | "kernel-escalated";

export interface PreSealIssue {
  readonly kind: PreSealIssueKind;
  readonly description: string;
  readonly blocking: boolean;
}

export interface PreSealReport {
  readonly issues: readonly PreSealIssue[];
  readonly blockingCount: number;
  readonly warningCount: number;
  readonly passed: boolean;
  readonly integrationCount: number;
  readonly checkedAt: number;
}

export const PRE_SEAL_IDLE: PreSealReport = Object.freeze({
  issues: Object.freeze([]) as readonly PreSealIssue[],
  blockingCount: 0,
  warningCount: 0,
  passed: true,
  integrationCount: 0,
  checkedAt: 0,
});
