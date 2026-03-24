/**
 * Alignment-Aware Posture Selector
 *
 * Adjusts the kernel's operational posture based on alignment level,
 * then applies constitutional safe mode override if active.
 *
 * Pipeline:
 *   1. Base posture adjustment by alignment tier
 *   2. Safe mode override (reduces responsiveness, raises caution)
 */

import type { StrategyEvaluation, KernelPosture } from "./types";
import { DEFAULT_KERNEL_POSTURE as DEFAULTS } from "./types";
import { applySafeModeToPosture } from "./safeMode";

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

export function selectPosture(
  strategy: StrategyEvaluation,
  basePosture: KernelPosture = { ...DEFAULTS },
): KernelPosture {
  let posture: KernelPosture;

  if (strategy.alignment >= 85) {
    posture = {
      responsiveness: clamp01(basePosture.responsiveness + 0.1),
      caution: basePosture.caution,
    };
  } else if (strategy.alignment < 70) {
    posture = {
      responsiveness: clamp01(basePosture.responsiveness - 0.2),
      caution: clamp01(basePosture.caution + 0.2),
    };
  } else {
    posture = { ...basePosture };
  }

  return applySafeModeToPosture(posture);
}
