/**
 * Alignment-Aware Escalation Rules
 *
 * Computes an escalation level based on the current strategy
 * evaluation's alignment score:
 *
 *   alignment < 50  → critical (autonomy should pause)
 *   alignment < 60  → high    (operator attention required)
 *   alignment < 70  → medium  (elevated monitoring)
 *   alignment ≥ 70  → none    (operating normally)
 *
 * The dispatcher uses this to override strategy when critical,
 * replacing it with `autonomy_paused_alignment_critical`.
 */

import type { StrategyEvaluation, EscalationResult } from "./types";

export function computeAlignmentEscalation(evaluation: StrategyEvaluation): EscalationResult {
  const { alignment } = evaluation;

  if (alignment < 50) {
    return { level: "critical", reason: `alignment_below_50 (${alignment}%)` };
  }

  if (alignment < 60) {
    return { level: "high", reason: `alignment_below_60 (${alignment}%)` };
  }

  if (alignment < 70) {
    return { level: "medium", reason: `alignment_below_70 (${alignment}%)` };
  }

  return { level: "none" };
}
