/**
 * Alignment-Aware Drift Detector
 *
 * Detects sustained downward trends in alignment using linear regression
 * slope over the measurement window, weighted by confidence.
 *
 * Improvements over endpoint-only comparison:
 *   - Linear regression slope captures the overall trend direction
 *   - Confidence weighting reduces the influence of uncertain readings
 *   - Configurable window and threshold via AlignmentPolicy
 */

import type { AlignmentHistoryPoint, AlignmentDriftResult } from "./types";
import { DEFAULT_ALIGNMENT_POLICY } from "./types";

const DRIFT_WINDOW = DEFAULT_ALIGNMENT_POLICY.driftWindow;
const DRIFT_THRESHOLD = DEFAULT_ALIGNMENT_POLICY.driftThreshold;

export function detectAlignmentDrift(history: AlignmentHistoryPoint[]): AlignmentDriftResult {
  const win = history.slice(-DRIFT_WINDOW);

  if (win.length < 2) {
    return { drifting: false, delta: 0, window: win.length, firstAlignment: null, lastAlignment: null };
  }

  const first = win[0].alignment;
  const last = win[win.length - 1].alignment;
  const endpointDelta = last - first;

  const slope = computeWeightedSlope(win);

  const projectedDelta = slope * (win.length - 1);

  return {
    drifting: projectedDelta <= -DRIFT_THRESHOLD,
    delta: Math.round(projectedDelta * 100) / 100,
    window: win.length,
    firstAlignment: first,
    lastAlignment: last,
  };
}

function computeWeightedSlope(points: AlignmentHistoryPoint[]): number {
  const n = points.length;
  if (n < 2) return 0;

  let sumW = 0, sumWX = 0, sumWY = 0, sumWXX = 0, sumWXY = 0;

  for (let i = 0; i < n; i++) {
    const w = Math.max(0.1, (points[i].confidence ?? 80) / 100);
    const x = i;
    const y = points[i].alignment;

    sumW += w;
    sumWX += w * x;
    sumWY += w * y;
    sumWXX += w * x * x;
    sumWXY += w * x * y;
  }

  const denom = sumW * sumWXX - sumWX * sumWX;
  if (Math.abs(denom) < 1e-10) return 0;

  return (sumW * sumWXY - sumWX * sumWY) / denom;
}

export { DRIFT_WINDOW, DRIFT_THRESHOLD };
