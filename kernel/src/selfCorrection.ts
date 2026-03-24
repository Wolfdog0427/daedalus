/**
 * Kernel Self-Correction Loop
 *
 * Monitors the recent alignment trend and automatically adjusts
 * kernel runtime config when alignment drops below the floor.
 * The floor is configurable via KernelRuntimeConfig.alignmentFloor
 * (runtime default: 60 via DEFAULT_KERNEL_CONFIG; fallback: 75
 * if alignmentFloor is undefined).
 */

import type {
  AlignmentHistoryPoint,
  AlignmentTrend,
  KernelRuntimeConfig,
} from "./types";

const ALIGNMENT_WINDOW = 20;
const ALIGNMENT_FLOOR_DEFAULT = 75;

const SENSITIVITY_STEP = 0.1;
const STRICTNESS_STEP = 0.05;

export function computeRecentAlignmentTrend(
  history: AlignmentHistoryPoint[],
  floor: number = ALIGNMENT_FLOOR_DEFAULT,
): AlignmentTrend {
  const recent = history.slice(-ALIGNMENT_WINDOW);

  if (recent.length === 0) {
    return { avgAlignment: null, belowFloor: false, sampleCount: 0 };
  }

  const avgAlignment = recent.reduce((sum, h) => sum + h.alignment, 0) / recent.length;

  return {
    avgAlignment: Math.round(avgAlignment * 100) / 100,
    belowFloor: avgAlignment < floor,
    sampleCount: recent.length,
  };
}

export function applySelfCorrectionIfNeeded(
  config: KernelRuntimeConfig,
  history: AlignmentHistoryPoint[],
): { config: KernelRuntimeConfig; corrected: boolean; trend: AlignmentTrend } {
  const floor = config.alignmentFloor ?? ALIGNMENT_FLOOR_DEFAULT;
  const trend = computeRecentAlignmentTrend(history, floor);

  if (trend.avgAlignment === null || !trend.belowFloor) {
    return { config, corrected: false, trend };
  }

  const corrected: KernelRuntimeConfig = {
    ...config,
    strategySensitivity: Math.max(0, config.strategySensitivity - SENSITIVITY_STEP),
    governanceStrictness: Math.min(1, config.governanceStrictness + STRICTNESS_STEP),
  };

  return { config: corrected, corrected: true, trend };
}

export { ALIGNMENT_WINDOW, ALIGNMENT_FLOOR_DEFAULT };
