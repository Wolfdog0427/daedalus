/**
 * Daedalus Alignment Regulation Loop
 *
 * Two-tier physiology:
 *  - Micro-corrections: continuous, gentle, always-on nudging toward alignment.
 *  - Macro-corrections: damped, constitutional interventions for large or
 *    accelerating drift.
 *
 * This is a pure function layer — it does NOT mutate global state. The kernel
 * integrates the returned decision into posture, safe mode, and escalation.
 *
 * Drift metrics (magnitude, slope, acceleration) are computed from alignment
 * history, giving the regulation loop a second-order view of system dynamics.
 */

import type {
  AlignmentHistoryPoint,
  DriftMetrics,
  RegulationConfig,
  RegulationOutput,
  SafeModeState,
} from "./types";
import { DEFAULT_REGULATION_CONFIG } from "./types";

let regulationConfig: RegulationConfig = { ...DEFAULT_REGULATION_CONFIG };
let lastRegulationOutput: RegulationOutput | null = null;

// ── Drift Computation ───────────────────────────────────────────────

const DRIFT_COMPUTATION_WINDOW = 40;

/**
 * Computes second-order drift metrics from alignment history.
 *
 * magnitude: |current_alignment - target|
 * slope: rate of change of drift magnitude (positive = worsening)
 * acceleration: rate of change of slope (positive = drift accelerating)
 */
export function computeDriftMetrics(
  history: AlignmentHistoryPoint[],
  target: number,
): DriftMetrics {
  if (history.length === 0) {
    return { magnitude: 0, slope: 0, acceleration: 0 };
  }

  const window = history.slice(-DRIFT_COMPUTATION_WINDOW);
  const current = window[window.length - 1].alignment;
  const magnitude = Math.abs(current - target);

  if (window.length < 2) {
    return { magnitude, slope: 0, acceleration: 0 };
  }

  const drifts = window.map(p => Math.abs(p.alignment - target));

  const first = drifts[0];
  const last = drifts[drifts.length - 1];
  const slope = (last - first) / (drifts.length - 1);

  let acceleration = 0;
  if (drifts.length >= 4) {
    const mid = Math.floor(drifts.length / 2);
    const slopeFirst = (drifts[mid] - drifts[0]) / mid;
    const slopeLast = (drifts[drifts.length - 1] - drifts[mid]) / (drifts.length - 1 - mid);
    acceleration = slopeLast - slopeFirst;
  }

  return {
    magnitude: round4(magnitude),
    slope: round4(slope),
    acceleration: round4(acceleration),
  };
}

// ── Core Regulation ─────────────────────────────────────────────────

export function regulateAlignment(
  alignment: number,
  driftMetrics: DriftMetrics,
  safeMode: SafeModeState,
  autonomyPaused: boolean,
  config: RegulationConfig = regulationConfig,
): RegulationOutput {
  const {
    targetAlignment,
    floorAlignment,
    microGain,
    macroGain,
    macroDamping,
    macroDriftThreshold,
    macroAccelerationThreshold,
    criticalAlignmentThreshold,
    catastrophicAlignmentThreshold,
  } = config;

  // ── 1. Micro-correction layer (continuous homeostasis) ──────────
  const directionToTarget =
    alignment < targetAlignment ? 1 :
    alignment > targetAlignment ? -1 : 0;

  const microBase = driftMetrics.magnitude * microGain * directionToTarget;
  const microAdjustment = clamp(microBase, -2, 2);

  // ── 2. Macro-correction layer (damped emergency response) ───────
  let macroRawCorrection = 0;
  let macroDampedCorrection = 0;
  let appliedMacro = false;
  let macroReason = "none";

  const largeDrift = driftMetrics.magnitude >= macroDriftThreshold;
  const acceleratingDrift = driftMetrics.acceleration >= macroAccelerationThreshold;

  if (largeDrift || acceleratingDrift) {
    macroRawCorrection = driftMetrics.magnitude * macroGain * directionToTarget;
    macroDampedCorrection = macroRawCorrection * macroDamping;
    macroDampedCorrection = clamp(macroDampedCorrection, -15, 15);
    appliedMacro = true;
    macroReason = largeDrift && acceleratingDrift
      ? "large_and_accelerating_drift"
      : largeDrift
        ? "large_drift"
        : "accelerating_drift";
  }

  // ── 3. Governance signals ───────────────────────────────────────
  let shouldEnterSafeMode = false;
  let shouldExitSafeMode = false;
  let shouldPauseAutonomy = false;
  let shouldResumeAutonomy = false;

  if (alignment <= catastrophicAlignmentThreshold && !safeMode.active) {
    shouldEnterSafeMode = true;
  }

  if (alignment <= criticalAlignmentThreshold && !autonomyPaused) {
    shouldPauseAutonomy = true;
  }

  // Exit safe mode when alignment is above floor AND either slope is improving
  // or alignment is comfortably above the exit threshold (prevents stuck-in-safe-mode
  // when magnitude is constant but above floor).
  const comfortablyAboveFloor = alignment >= floorAlignment + 5;
  if (safeMode.active && alignment >= floorAlignment && (driftMetrics.slope < 0 || comfortablyAboveFloor)) {
    shouldExitSafeMode = true;
  }

  // Resume autonomy with the same comfort-above-floor fallback
  if (autonomyPaused && alignment >= floorAlignment && (driftMetrics.acceleration <= 0 || comfortablyAboveFloor)) {
    shouldResumeAutonomy = true;
  }

  const output: RegulationOutput = {
    microAdjustment,
    macroAdjustment: appliedMacro ? macroDampedCorrection : 0,
    shouldEnterSafeMode,
    shouldExitSafeMode,
    shouldPauseAutonomy,
    shouldResumeAutonomy,
    driftMetrics,
    telemetry: {
      appliedMicro: microAdjustment !== 0,
      appliedMacro,
      macroRawCorrection: round4(macroRawCorrection),
      macroDampedCorrection: round4(macroDampedCorrection),
      reason: macroReason,
    },
  };

  lastRegulationOutput = output;
  return output;
}

/**
 * Runs the full regulation pipeline: computes drift from history,
 * then regulates. This is the integration entry point for tickKernel.
 */
export function runRegulation(
  history: AlignmentHistoryPoint[],
  currentAlignment: number,
  safeMode: SafeModeState,
  autonomyPaused: boolean,
  config?: RegulationConfig,
): RegulationOutput {
  const cfg = config ?? regulationConfig;
  const driftMetrics = computeDriftMetrics(history, cfg.targetAlignment);
  return regulateAlignment(currentAlignment, driftMetrics, safeMode, autonomyPaused, cfg);
}

// ── Posture Modulation ──────────────────────────────────────────────

import type { KernelPosture } from "./types";

/**
 * Applies regulation adjustments to posture. Micro-corrections gently
 * nudge responsiveness/caution; macro-corrections create larger shifts.
 */
export function applyRegulationToPosture(
  posture: KernelPosture,
  regulation: RegulationOutput,
): KernelPosture {
  let { responsiveness, caution } = posture;

  if (regulation.telemetry.appliedMicro) {
    const microFactor = regulation.microAdjustment / 100;
    responsiveness = clamp01(responsiveness - microFactor);
    caution = clamp01(caution + microFactor);
  }

  if (regulation.telemetry.appliedMacro) {
    const macroFactor = regulation.macroAdjustment / 100;
    responsiveness = clamp01(responsiveness - macroFactor * 0.5);
    caution = clamp01(caution + macroFactor * 0.5);
  }

  return { responsiveness, caution };
}

// ── Config Management ───────────────────────────────────────────────

export function getRegulationConfig(): RegulationConfig {
  return { ...regulationConfig };
}

export function updateRegulationConfig(patch: Partial<RegulationConfig>): RegulationConfig {
  regulationConfig = { ...regulationConfig, ...patch };
  return { ...regulationConfig };
}

export function getLastRegulationOutput(): RegulationOutput | null {
  return lastRegulationOutput ? { ...lastRegulationOutput } : null;
}

export function resetRegulationState(): void {
  regulationConfig = { ...DEFAULT_REGULATION_CONFIG };
  lastRegulationOutput = null;
}

// ── Helpers ─────────────────────────────────────────────────────────

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

function round4(v: number): number {
  return Math.round(v * 10000) / 10000;
}

export { DRIFT_COMPUTATION_WINDOW };
