/**
 * Alignment-Aware Strategy Gating
 *
 * Gates strategy evaluations based on alignment level:
 *
 * - alignment ≥ 80: pass-through (strategy is trusted)
 * - alignment 60–79: replaced with alignment_guard_cautious
 *   (strategy is allowed but flagged as cautious)
 * - alignment < 60: replaced with alignment_guard_critical
 *   (strategy is overridden — system must recover alignment first)
 *
 * Gated evaluations preserve the original strategy name in
 * `originalStrategy` and set `gated: true` for downstream consumers.
 */

import type { StrategyEvaluation, SharedStrategyName } from "./types";

const GATE_PASS_THRESHOLD = 80;
const GATE_CAUTIOUS_THRESHOLD = 60;

export function gateStrategyByAlignment(evaluation: StrategyEvaluation): StrategyEvaluation {
  if (evaluation.alignment >= GATE_PASS_THRESHOLD) {
    return evaluation;
  }

  const original = evaluation.name as SharedStrategyName;

  if (evaluation.alignment < GATE_CAUTIOUS_THRESHOLD) {
    return {
      ...evaluation,
      name: "alignment_guard_critical",
      gated: true,
      originalStrategy: original,
      notes: `Strategy ${original} gated: alignment ${evaluation.alignment}% below critical threshold (${GATE_CAUTIOUS_THRESHOLD}%). ${evaluation.notes}`,
    };
  }

  return {
    ...evaluation,
    name: "alignment_guard_cautious",
    gated: true,
    originalStrategy: original,
    notes: `Strategy ${original} gated: alignment ${evaluation.alignment}% below preferred threshold (${GATE_PASS_THRESHOLD}%). ${evaluation.notes}`,
  };
}

export { GATE_PASS_THRESHOLD, GATE_CAUTIOUS_THRESHOLD };
