/**
 * Alignment-Aware Escalation Rules
 *
 * Computes an escalation level based on alignment score and confidence.
 * Thresholds are drawn from the unified AlignmentPolicy.
 *
 *   alignment < 50  → critical (autonomy should pause)
 *   alignment < 60  → high    (operator attention required)
 *   alignment < 70  → medium  (elevated monitoring)
 *   alignment ≥ 70  → none    (operating normally)
 *
 * Low confidence (< 50) at any level bumps escalation up by one tier
 * to reflect the reduced certainty in the alignment reading.
 */

import type { StrategyEvaluation, EscalationResult, EscalationLevel } from "./types";
import { DEFAULT_ALIGNMENT_POLICY } from "./types";

const CRITICAL = DEFAULT_ALIGNMENT_POLICY.escalationCriticalThreshold;
const HIGH = DEFAULT_ALIGNMENT_POLICY.escalationHighThreshold;
const MEDIUM = DEFAULT_ALIGNMENT_POLICY.escalationMediumThreshold;
const CONFIDENCE_BUMP_THRESHOLD = 35;
const HYSTERESIS = 3;

let currentLevel: EscalationLevel = "none";

const LEVEL_ORDER: EscalationLevel[] = ["none", "medium", "high", "critical"];

function levelIndex(l: EscalationLevel): number {
  return LEVEL_ORDER.indexOf(l);
}

export function computeAlignmentEscalation(evaluation: StrategyEvaluation): EscalationResult {
  const { alignment, confidence } = evaluation;
  const lowConfidence = confidence < CONFIDENCE_BUMP_THRESHOLD;

  let rawLevel: EscalationLevel;
  let reason: string | undefined;

  if (alignment < CRITICAL) {
    rawLevel = "critical";
    reason = `alignment_below_${CRITICAL} (${alignment}%)`;
  } else if (alignment < HIGH) {
    rawLevel = lowConfidence ? "critical" : "high";
    reason = lowConfidence
      ? `alignment_below_${HIGH} (${alignment}%) + low confidence (${confidence}%)`
      : `alignment_below_${HIGH} (${alignment}%)`;
  } else if (alignment < MEDIUM) {
    rawLevel = lowConfidence ? "high" : "medium";
    reason = lowConfidence
      ? `alignment_below_${MEDIUM} (${alignment}%) + low confidence (${confidence}%)`
      : `alignment_below_${MEDIUM} (${alignment}%)`;
  } else if (lowConfidence) {
    rawLevel = "medium";
    reason = `alignment OK (${alignment}%) but low confidence (${confidence}%)`;
  } else {
    rawLevel = "none";
  }

  const rawIdx = levelIndex(rawLevel);
  const curIdx = levelIndex(currentLevel);

  if (rawIdx > curIdx) {
    currentLevel = rawLevel;
  } else if (rawIdx < curIdx) {
    // C3: Fast de-escalation — when raw level is 2+ tiers below current
    // AND alignment is trending upward (approximated by alignment > exit threshold),
    // allow jumping directly instead of stepping down one tier at a time.
    if (rawIdx <= curIdx - 2) {
      currentLevel = rawLevel;
    } else {
      const exitThreshold = rawLevel === "none" ? MEDIUM + HYSTERESIS
        : rawLevel === "medium" ? HIGH + HYSTERESIS
        : rawLevel === "high" ? CRITICAL + HYSTERESIS
        : 0;
      if (alignment >= exitThreshold) {
        currentLevel = rawLevel;
      }
    }
  }

  return { level: currentLevel, reason };
}

export function resetEscalation(): void {
  currentLevel = "none";
}
