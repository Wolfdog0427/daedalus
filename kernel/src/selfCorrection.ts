/**
 * Kernel Self-Correction Loop
 *
 * Monitors the recent alignment trend and automatically adjusts
 * kernel runtime config:
 *   - When alignment drops below the floor: tightens (sensitivity down,
 *     strictness up) — fast, aggressive.
 *   - When alignment is sustained above target: relaxes (sensitivity up,
 *     strictness down) — slow, gentle, asymmetric toward safety.
 *
 * The floor is configurable via KernelRuntimeConfig.alignmentFloor
 * (runtime default: 60 via DEFAULT_KERNEL_CONFIG; fallback: 75
 * if alignmentFloor is undefined).
 */

import type {
  AlignmentHistoryPoint,
  AlignmentTrend,
  KernelRuntimeConfig,
} from "./types";
import { DEFAULT_ALIGNMENT_POLICY } from "./types";

const ALIGNMENT_WINDOW = DEFAULT_ALIGNMENT_POLICY.selfCorrectionWindow;
const ALIGNMENT_FLOOR_DEFAULT = DEFAULT_ALIGNMENT_POLICY.selfCorrectionFloorDefault;

const TIGHTEN_SENSITIVITY_STEP = 0.1;
const TIGHTEN_STRICTNESS_STEP = 0.05;
const RELAX_SENSITIVITY_STEP = 0.02;
const RELAX_STRICTNESS_STEP = 0.01;
const RELAX_TARGET = 92;
const RELAX_SUSTAINED_SAMPLES = 15;

let operatorBaseline: { sensitivity: number; strictness: number } | null = null;

export function setOperatorConfigBaseline(config: KernelRuntimeConfig): void {
  operatorBaseline = {
    sensitivity: config.strategySensitivity,
    strictness: config.governanceStrictness,
  };
}

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

  if (trend.avgAlignment === null) {
    return { config, corrected: false, trend };
  }

  if (trend.belowFloor) {
    const corrected: KernelRuntimeConfig = {
      ...config,
      strategySensitivity: Math.max(0, config.strategySensitivity - TIGHTEN_SENSITIVITY_STEP),
      governanceStrictness: Math.min(1, config.governanceStrictness + TIGHTEN_STRICTNESS_STEP),
    };
    return { config: corrected, corrected: true, trend };
  }

  const recent = history.slice(-ALIGNMENT_WINDOW);
  const allAboveTarget = recent.length >= RELAX_SUSTAINED_SAMPLES &&
    recent.slice(-RELAX_SUSTAINED_SAMPLES).every(p => p.alignment >= RELAX_TARGET);

  if (allAboveTarget) {
    const sensTarget = operatorBaseline ? operatorBaseline.sensitivity : 1.0;
    const strictTarget = operatorBaseline ? operatorBaseline.strictness : 0.8;
    const canRelaxSensitivity = config.strategySensitivity < sensTarget;
    const canRelaxStrictness = config.governanceStrictness > strictTarget;

    if (canRelaxSensitivity || canRelaxStrictness) {
      const sensFloor = operatorBaseline ? operatorBaseline.sensitivity : 1.0;
      const strictFloor = operatorBaseline ? operatorBaseline.strictness : 0.8;
      const relaxed: KernelRuntimeConfig = {
        ...config,
        strategySensitivity: Math.min(sensFloor, config.strategySensitivity + RELAX_SENSITIVITY_STEP),
        governanceStrictness: Math.max(strictFloor, config.governanceStrictness - RELAX_STRICTNESS_STEP),
      };
      return { config: relaxed, corrected: true, trend };
    }
  }

  return { config, corrected: false, trend };
}

export { ALIGNMENT_WINDOW, ALIGNMENT_FLOOR_DEFAULT };
