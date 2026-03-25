/**
 * Constitutional Safe Mode
 *
 * When alignment drops below the enter threshold for a sustained number
 * of consecutive ticks, the kernel enters safe mode:
 * - Reduces responsiveness sharply (-0.3)
 * - Raises caution sharply (+0.3)
 *
 * Instant entry (bypassing sustained-ticks requirement) occurs when
 * alignment drops below the instant threshold (default: 20%).
 *
 * Safe mode exits when alignment recovers to >= exit threshold (65%)
 * with hysteresis to prevent oscillation.
 */

import type { StrategyEvaluation, KernelPosture, SafeModeState } from "./types";
import { DEFAULT_ALIGNMENT_POLICY } from "./types";

let safeMode: SafeModeState = { active: false };
let consecutiveBelowCount = 0;

const SAFE_MODE_ENTER_THRESHOLD = DEFAULT_ALIGNMENT_POLICY.safeModeEnterThreshold;
const SAFE_MODE_EXIT_THRESHOLD = DEFAULT_ALIGNMENT_POLICY.safeModeExitThreshold;
const SAFE_MODE_INSTANT_THRESHOLD = DEFAULT_ALIGNMENT_POLICY.safeModeInstantThreshold;
const SAFE_MODE_SUSTAINED_TICKS = DEFAULT_ALIGNMENT_POLICY.safeModeEnterSustainedTicks;

export function getSafeModeState(): SafeModeState {
  return { ...safeMode };
}

export function updateSafeModeFromAlignment(evaluation: StrategyEvaluation): void {
  if (evaluation.alignment < SAFE_MODE_ENTER_THRESHOLD) {
    consecutiveBelowCount++;

    const instantEntry = evaluation.alignment < SAFE_MODE_INSTANT_THRESHOLD;
    const sustainedEntry = consecutiveBelowCount >= SAFE_MODE_SUSTAINED_TICKS;

    if (!safeMode.active && (instantEntry || sustainedEntry)) {
      safeMode = {
        active: true,
        reason: instantEntry
          ? `alignment_instant_critical (${evaluation.alignment}%)`
          : `alignment_below_${SAFE_MODE_ENTER_THRESHOLD}_sustained (${evaluation.alignment}%, ${consecutiveBelowCount} ticks)`,
        since: Date.now(),
      };
    }
  } else {
    consecutiveBelowCount = Math.max(0, consecutiveBelowCount - 1);

    if (safeMode.active && evaluation.alignment >= SAFE_MODE_EXIT_THRESHOLD) {
      safeMode = { active: false };
    }
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
  consecutiveBelowCount = 0;
}

export { SAFE_MODE_ENTER_THRESHOLD, SAFE_MODE_EXIT_THRESHOLD };
