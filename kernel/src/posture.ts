/**
 * Alignment-Aware Posture Selector
 *
 * Adjusts the kernel's operational posture using continuous/graduated
 * mapping based on alignment level, rather than discrete 3-band jumps.
 *
 * The mapping uses linear interpolation:
 *   - alignment >= 92 (target): max responsiveness boost, no caution change
 *   - alignment  = 70 (floor):  no change (neutral point)
 *   - alignment <= 50 (critical): max responsiveness reduction, max caution
 *
 * Between these anchor points, adjustments interpolate smoothly.
 * Safe mode overlay is applied separately downstream.
 */

import type { StrategyEvaluation, KernelPosture, MicroPosture, AlignmentDriftResult } from "./types";
import { DEFAULT_KERNEL_POSTURE as DEFAULTS, SubPosture } from "./types";
import { applySafeModeToPosture } from "./safeMode";

const ANCHOR_HIGH = 92;
const ANCHOR_NEUTRAL = 70;
const ANCHOR_LOW = 50;

const MAX_RESP_BOOST = 0.15;
const MAX_RESP_REDUCTION = 0.25;
const MAX_CAUTION_BOOST = 0.25;

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * Math.max(0, Math.min(1, t));
}

export function selectPosture(
  strategy: StrategyEvaluation,
  basePosture: KernelPosture = { ...DEFAULTS },
): KernelPosture {
  const alignment = strategy.alignment;
  let respAdj = 0;
  let cautAdj = 0;

  if (alignment >= ANCHOR_NEUTRAL) {
    const t = (alignment - ANCHOR_NEUTRAL) / (ANCHOR_HIGH - ANCHOR_NEUTRAL);
    respAdj = lerp(0, MAX_RESP_BOOST, t);
  } else {
    const t = (ANCHOR_NEUTRAL - alignment) / (ANCHOR_NEUTRAL - ANCHOR_LOW);
    respAdj = -lerp(0, MAX_RESP_REDUCTION, t);
    cautAdj = lerp(0, MAX_CAUTION_BOOST, t);
  }

  const posture: KernelPosture = {
    responsiveness: clamp01(basePosture.responsiveness + respAdj),
    caution: clamp01(basePosture.caution + cautAdj),
  };

  return applySafeModeToPosture(posture, alignment);
}

// ── Sub-Posture Selection ───────────────────────────────────────────

export interface SubPostureContext {
  operatorTrustScore: number;
  cognitiveLoad: number;
  creativeTask: boolean;
  sensitiveOperator: boolean;
}

export function selectSubPosture(
  alignment: number,
  drift: AlignmentDriftResult,
  operatorTrust: number,
  context: SubPostureContext = { operatorTrustScore: 0, cognitiveLoad: 0, creativeTask: false, sensitiveOperator: false },
): SubPosture {
  if (alignment < 50) return SubPosture.DEFENSIVE;
  if (drift.drifting && Math.abs(drift.delta) > 10) return SubPosture.DEFENSIVE;
  if (context.sensitiveOperator) return SubPosture.SENSITIVE;
  if (context.creativeTask) return SubPosture.CREATIVE;
  if (context.cognitiveLoad > 0.7) return SubPosture.ANALYTIC;
  if (operatorTrust >= 85) return SubPosture.SUPPORTIVE;
  return SubPosture.NONE;
}

// ── Micro-Posture (continuous modulation) ────────────────────────────

export function computeMicroPosture(
  alignment: number,
  confidence: number,
  drift: AlignmentDriftResult,
): MicroPosture {
  const driftDampen = drift.drifting ? 0.15 : 0;
  return {
    responsiveness: clamp01(alignment / 100),
    caution: clamp01(1 - alignment / 100 + driftDampen),
    expressiveness: clamp01(confidence / 100 - driftDampen),
  };
}
