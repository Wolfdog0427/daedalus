/**
 * Alignment-Confidence Coupling
 *
 * Computes a running system-level confidence score derived from:
 *   - Current alignment level (60% weight)
 *   - Alignment stability / low variance (25% weight)
 *   - Alignment trajectory / drift slope (15% weight)
 *
 * This score drives behavioral modifiers that make the organism
 * more fluid and autonomous when aligned, and more cautious and
 * conservative when degraded.
 *
 * SAFETY INVARIANTS (never violated):
 *   - Correction damping is ALWAYS 0 during active safe mode
 *   - Confidence NEVER overrides constitutional safety mechanisms
 *   - Safe mode, escalation, and operator trust gates are unaffected
 *   - The score is behavioral, not constitutional
 */

import type { AlignmentHistoryPoint, DriftMetrics, SafeModeState, SystemConfidence } from "./types";
import { INITIAL_SYSTEM_CONFIDENCE } from "./types";

const STABILITY_WINDOW = 40;
const STABILITY_VARIANCE_SCALE = 3;

let lastConfidence: SystemConfidence = { ...INITIAL_SYSTEM_CONFIDENCE };

export function computeSystemConfidence(
  currentAlignment: number,
  history: AlignmentHistoryPoint[],
  driftMetrics: DriftMetrics,
  safeMode: SafeModeState,
): SystemConfidence {
  const alignmentBasis = currentAlignment;

  // Stability: low variance in recent alignment → high stability
  const window = history.slice(-STABILITY_WINDOW);
  let stabilityBonus = 50;
  if (window.length >= 4) {
    const values = window.map(p => p.alignment);
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / values.length;
    const stdDev = Math.sqrt(variance);
    stabilityBonus = clamp(100 - stdDev * STABILITY_VARIANCE_SCALE, 0, 100);
  }

  // Trajectory: negative slope = drift shrinking = alignment improving
  const trajectoryBonus = clamp(50 - driftMetrics.slope * 10, 0, 100);

  const raw = alignmentBasis * 0.60 + stabilityBonus * 0.25 + trajectoryBonus * 0.15;
  const score = clamp(Math.round(raw), 0, 100);

  // ── Behavioral Modifiers ──────────────────────────────────────────

  // Approval bias: shifts auto-approval alignment threshold
  // score 90 → +10 (threshold 85), score 70 → 0, score 40 → -15
  const approvalBias = clamp(Math.round((score - 70) * 0.5), -15, 10);

  // Proposal readiness: how proactively to generate proposals
  const proposalReadiness = round2(clamp((score - 30) / 60, 0, 1));

  // Expressive range: width of sub-posture / overlay selection
  const expressiveRange = round2(clamp(score / 100, 0.1, 1));

  // Correction damping: reduce correction intensity when stable & aligned
  // SAFETY: forced to 0 during safe mode so recovery runs at full speed
  let correctionDamping = round2(clamp((score - 50) / 71.4, 0, 0.7));
  if (safeMode.active) correctionDamping = 0;

  const confidence: SystemConfidence = {
    score,
    alignmentBasis: Math.round(alignmentBasis),
    stabilityBonus: Math.round(stabilityBonus),
    trajectoryBonus: Math.round(trajectoryBonus),
    approvalBias,
    proposalReadiness,
    expressiveRange,
    correctionDamping,
  };

  lastConfidence = confidence;
  return confidence;
}

export function getLastSystemConfidence(): SystemConfidence {
  return { ...lastConfidence };
}

export function resetSystemConfidence(): void {
  lastConfidence = { ...INITIAL_SYSTEM_CONFIDENCE };
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

function round2(v: number): number {
  return Math.round(v * 100) / 100;
}
