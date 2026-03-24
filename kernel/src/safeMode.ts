/**
 * Constitutional Safe Mode
 *
 * When alignment drops below 50%, the kernel enters safe mode:
 * - Reduces responsiveness sharply (-0.3)
 * - Raises caution sharply (+0.3)
 *
 * Safe mode exits when alignment recovers to ≥ 65% (hysteresis
 * prevents oscillation between normal and safe mode).
 *
 * Safe mode state is exposed in the telemetry snapshot and
 * the strategy API response for cockpit display.
 */

import type { StrategyEvaluation, KernelPosture, SafeModeState } from "./types";

let safeMode: SafeModeState = { active: false };

const SAFE_MODE_ENTER_THRESHOLD = 50;
const SAFE_MODE_EXIT_THRESHOLD = 65;

export function getSafeModeState(): SafeModeState {
  return { ...safeMode };
}

export function updateSafeModeFromAlignment(evaluation: StrategyEvaluation): void {
  if (evaluation.alignment < SAFE_MODE_ENTER_THRESHOLD) {
    if (!safeMode.active) {
      safeMode = {
        active: true,
        reason: `alignment_below_${SAFE_MODE_ENTER_THRESHOLD} (${evaluation.alignment}%)`,
        since: Date.now(),
      };
    }
  } else if (safeMode.active && evaluation.alignment >= SAFE_MODE_EXIT_THRESHOLD) {
    safeMode = { active: false };
  }
}

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

export function applySafeModeToPosture(posture: KernelPosture): KernelPosture {
  if (!safeMode.active) return posture;

  return {
    responsiveness: clamp01(posture.responsiveness - 0.3),
    caution: clamp01(posture.caution + 0.3),
  };
}

export function resetSafeMode(): void {
  safeMode = { active: false };
}

export { SAFE_MODE_ENTER_THRESHOLD, SAFE_MODE_EXIT_THRESHOLD };
