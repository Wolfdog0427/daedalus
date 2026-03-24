/**
 * Alignment-Aware Drift Detector
 *
 * Detects sustained downward trends in alignment over a configurable
 * window of recent evaluations. A drift is declared when the most
 * recent alignment drops DRIFT_THRESHOLD or more percentage points
 * below the earliest alignment in the window.
 *
 * Used by:
 * - telemetry snapshot (exposed to API and cockpit)
 * - self-correction loop (triggers config adjustment)
 */

import type { AlignmentHistoryPoint, AlignmentDriftResult } from "./types";

const DRIFT_WINDOW = 40;
const DRIFT_THRESHOLD = 10;

export function detectAlignmentDrift(history: AlignmentHistoryPoint[]): AlignmentDriftResult {
  const window = history.slice(-DRIFT_WINDOW);

  if (window.length < 2) {
    return { drifting: false, delta: 0, window: window.length, firstAlignment: null, lastAlignment: null };
  }

  const first = window[0].alignment;
  const last = window[window.length - 1].alignment;
  const delta = last - first;

  return {
    drifting: delta <= -DRIFT_THRESHOLD,
    delta,
    window: window.length,
    firstAlignment: first,
    lastAlignment: last,
  };
}

export { DRIFT_WINDOW, DRIFT_THRESHOLD };
