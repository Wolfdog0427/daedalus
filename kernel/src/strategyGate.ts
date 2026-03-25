/**
 * Alignment-Aware Strategy Gating
 *
 * Gates strategy evaluations based on alignment and confidence levels.
 *
 * Uses hysteresis bands to prevent threshold flapping: to transition
 * up (e.g., cautious → stable), alignment must exceed threshold + hysteresisUp;
 * to drop down, it must fall below threshold - hysteresisDown.
 *
 * Band naming is aligned with escalation levels:
 *   - alignment_guard_high: alignment < cautious threshold (matches "high" escalation)
 *   - alignment_guard_cautious: alignment < pass threshold
 *   - Pass-through when alignment >= pass threshold and confidence >= minimum
 */

import type { StrategyEvaluation, SharedStrategyName } from "./types";
import { DEFAULT_ALIGNMENT_POLICY } from "./types";

const GATE_PASS_THRESHOLD = DEFAULT_ALIGNMENT_POLICY.gatePassThreshold;
const GATE_CAUTIOUS_THRESHOLD = DEFAULT_ALIGNMENT_POLICY.gateCautiousThreshold;
const HYSTERESIS_UP = DEFAULT_ALIGNMENT_POLICY.gateHysteresisUp;
const HYSTERESIS_DOWN = DEFAULT_ALIGNMENT_POLICY.gateHysteresisDown;
const CONFIDENCE_MINIMUM = 40;

type GateBand = "stable" | "cautious" | "high";
let currentBand: GateBand = "stable";

export function gateStrategyByAlignment(evaluation: StrategyEvaluation): StrategyEvaluation {
  const { alignment, confidence } = evaluation;

  const newBand = computeBandWithHysteresis(alignment, confidence);
  currentBand = newBand;

  if (newBand === "stable") {
    return evaluation;
  }

  const original = evaluation.name as SharedStrategyName;

  if (newBand === "high") {
    return {
      ...evaluation,
      name: "alignment_guard_critical",
      gated: true,
      originalStrategy: original,
      notes: `Strategy ${original} gated: alignment ${alignment}% below high threshold (${GATE_CAUTIOUS_THRESHOLD}%). ${evaluation.notes}`,
    };
  }

  return {
    ...evaluation,
    name: "alignment_guard_cautious",
    gated: true,
    originalStrategy: original,
    notes: `Strategy ${original} gated: alignment ${alignment}% below preferred threshold (${GATE_PASS_THRESHOLD}%). ${evaluation.notes}`,
  };
}

function computeBandWithHysteresis(alignment: number, confidence: number): GateBand {
  const lowConfidence = confidence < CONFIDENCE_MINIMUM;

  switch (currentBand) {
    case "stable":
      if (alignment < GATE_CAUTIOUS_THRESHOLD - HYSTERESIS_DOWN) return "high";
      if (alignment < GATE_PASS_THRESHOLD - HYSTERESIS_DOWN || lowConfidence) return "cautious";
      return "stable";

    case "cautious":
      if (alignment < GATE_CAUTIOUS_THRESHOLD - HYSTERESIS_DOWN) return "high";
      if (alignment >= GATE_PASS_THRESHOLD + HYSTERESIS_UP && !lowConfidence) return "stable";
      return "cautious";

    case "high":
      if (alignment >= GATE_PASS_THRESHOLD + HYSTERESIS_UP && !lowConfidence) return "stable";
      if (alignment >= GATE_CAUTIOUS_THRESHOLD + HYSTERESIS_UP) return "cautious";
      return "high";
  }
}

export function resetGateBand(): void {
  currentBand = "stable";
}

export { GATE_PASS_THRESHOLD, GATE_CAUTIOUS_THRESHOLD };
