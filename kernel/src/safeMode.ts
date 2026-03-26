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
 * Safe mode exits when alignment recovers to >= exit threshold (60%)
 * with hysteresis to prevent oscillation.
 */

import type { StrategyEvaluation, KernelPosture, SafeModeState } from "./types";
import { DEFAULT_ALIGNMENT_POLICY } from "./types";

let safeMode: SafeModeState = { active: false };
let consecutiveBelowCount = 0;
let consecutiveAboveExitCount = 0;
let reEntryCooldown = 0;

const SAFE_MODE_ENTER_THRESHOLD = DEFAULT_ALIGNMENT_POLICY.safeModeEnterThreshold;
const SAFE_MODE_EXIT_THRESHOLD = DEFAULT_ALIGNMENT_POLICY.safeModeExitThreshold;
const SAFE_MODE_INSTANT_THRESHOLD = DEFAULT_ALIGNMENT_POLICY.safeModeInstantThreshold;
const SAFE_MODE_SUSTAINED_TICKS = DEFAULT_ALIGNMENT_POLICY.safeModeEnterSustainedTicks;

const SUSTAINED_EXIT_TICKS = 3;
const RE_ENTRY_COOLDOWN_TICKS = 10;

export function getSafeModeState(): SafeModeState {
  return { ...safeMode };
}

export function updateSafeModeFromAlignment(evaluation: StrategyEvaluation): void {
  if (reEntryCooldown > 0) reEntryCooldown--;

  if (evaluation.alignment < SAFE_MODE_ENTER_THRESHOLD) {
    consecutiveBelowCount++;
    consecutiveAboveExitCount = 0;

    const instantEntry = evaluation.alignment < SAFE_MODE_INSTANT_THRESHOLD;
    const sustainedEntry = consecutiveBelowCount >= SAFE_MODE_SUSTAINED_TICKS;
    const cooldownAllows = reEntryCooldown === 0 || instantEntry;

    if (!safeMode.active && (instantEntry || sustainedEntry) && cooldownAllows) {
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
      consecutiveAboveExitCount++;
      if (consecutiveAboveExitCount >= SUSTAINED_EXIT_TICKS) {
        safeMode = { active: false };
        consecutiveAboveExitCount = 0;
        reEntryCooldown = RE_ENTRY_COOLDOWN_TICKS;
      }
    } else {
      consecutiveAboveExitCount = 0;
    }
  }
}

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

/**
 * M3: Graduated safe mode — penalty scales with alignment depth.
 * Full penalty at alignment <= 20, proportional ramp between 20-60.
 */
export function applySafeModeToPosture(posture: KernelPosture, alignment?: number): KernelPosture {
  if (!safeMode.active) return posture;

  const al = alignment ?? 0;
  const factor = clamp01((SAFE_MODE_EXIT_THRESHOLD - al) / (SAFE_MODE_EXIT_THRESHOLD - SAFE_MODE_INSTANT_THRESHOLD));

  return {
    responsiveness: clamp01(posture.responsiveness - 0.3 * factor),
    caution: clamp01(posture.caution + 0.3 * factor),
  };
}

export function enterSafeModeFromRegulation(reason: string): void {
  if (!safeMode.active && reEntryCooldown === 0) {
    safeMode = { active: true, reason, since: Date.now() };
  }
}

export function exitSafeModeFromRegulation(): void {
  if (safeMode.active) {
    safeMode = { active: false };
    consecutiveBelowCount = 0;
    consecutiveAboveExitCount = 0;
    reEntryCooldown = RE_ENTRY_COOLDOWN_TICKS;
  }
}

export function resetSafeMode(): void {
  safeMode = { active: false };
  consecutiveBelowCount = 0;
  consecutiveAboveExitCount = 0;
  reEntryCooldown = 0;
}

export { SAFE_MODE_ENTER_THRESHOLD, SAFE_MODE_EXIT_THRESHOLD };
