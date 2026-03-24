/**
 * Kernel Strategy Evaluator
 *
 * Wraps the shared alignment engine with kernel-level enrichments:
 * - computeAlignmentBreakdown: produces a four-axis breakdown given
 *   a strategy name and live AlignmentContext
 * - explainStrategy: derives human-readable notes from the evaluation
 * - evaluateStrategy: full pipeline returning the enriched StrategyEvaluation
 *
 * The kernel's evaluateStrategy is the canonical entry point that the
 * dispatcher calls — it always returns alignment + breakdown + notes.
 */

import {
  computeAlignmentBreakdown as sharedComputeBreakdown,
  computeAlignment,
  deriveStrategyName,
  scoreSovereignty,
  scoreIdentity,
  scoreGovernance,
  scoreStability,
  DEFAULT_ALIGNMENT_WEIGHTS,
  type AlignmentBreakdown,
  type AlignmentContext,
  type StrategyEvaluation,
  type StrategyName as SharedStrategyName,
} from "../../shared/daedalus/strategyAlignment";
import { computeIdentityContinuity, type IdentitySnapshot } from "./identity";
import type { StrategyName } from "./types";

function clamp(v: number, min = 0, max = 100): number {
  return Math.min(max, Math.max(min, v));
}

function axisExtreme(b: AlignmentBreakdown, pick: "min" | "max"): keyof AlignmentBreakdown {
  const entries = Object.entries(b) as [keyof AlignmentBreakdown, number][];
  return entries.reduce((best, [k, v]) => {
    const cmp = pick === "min" ? v < best[1] : v > best[1];
    return cmp ? [k, v] : best;
  }, entries[0])[0];
}

/**
 * Kernel-level breakdown computation. Uses the shared scorers but allows
 * strategy-specific bias adjustments based on the named strategy so
 * repeated evaluations for the same context can reflect intentional posture.
 */
export function computeAlignmentBreakdown(
  strategyName: StrategyName | null,
  ctx: AlignmentContext,
): AlignmentBreakdown {
  const base = sharedComputeBreakdown(ctx);

  const identitySnapshot: IdentitySnapshot = {
    posture: ctx.posture,
    mode: (ctx as any).mode,
    governanceTier: (ctx as any).governanceTier,
  };
  const identityContinuity = computeIdentityContinuity(identitySnapshot);
  base.identity = clamp(Math.round(base.identity * 0.7 + identityContinuity * 0.3));

  if (!strategyName) return base;

  const bias = strategyBias(strategyName);
  return {
    sovereignty: clamp(base.sovereignty + bias.sovereignty),
    identity: clamp(base.identity + bias.identity),
    governance: clamp(base.governance + bias.governance),
    stability: clamp(base.stability + bias.stability),
  };
}

/**
 * Strategy-specific scoring bias. When the system is intentionally in a
 * named strategy, certain axes receive minor boosts or penalties to
 * reflect the deliberate posture shift.
 */
function strategyBias(name: StrategyName): AlignmentBreakdown {
  switch (name) {
    case "sovereignty_stable":
      return { sovereignty: 3, identity: 0, governance: 0, stability: 0 };
    case "sovereignty_contested":
      return { sovereignty: -5, identity: 0, governance: 2, stability: 0 };
    case "identity_reinforcement":
      return { sovereignty: 0, identity: -3, governance: 0, stability: 1 };
    case "governance_attentive":
      return { sovereignty: 0, identity: 0, governance: -2, stability: 0 };
    case "governance_undercorrection":
      return { sovereignty: 2, identity: 0, governance: -4, stability: 0 };
    case "stability_recovery":
      return { sovereignty: 0, identity: 0, governance: 0, stability: -5 };
    case "alignment_nominal":
      return { sovereignty: 0, identity: 0, governance: 0, stability: 0 };
    case "alignment_degraded":
      return { sovereignty: -2, identity: -2, governance: -2, stability: -2 };
    case "alignment_guard_critical":
    case "alignment_guard_cautious":
    case "autonomy_paused_alignment_critical":
    default:
      return { sovereignty: 0, identity: 0, governance: 0, stability: 0 };
  }
}

/**
 * Generate human-readable notes for the given strategy + breakdown.
 * Richer than the shared `strategyNotes` — includes axis spread analysis
 * and actionable guidance.
 */
export function explainStrategy(
  name: StrategyName,
  breakdown: AlignmentBreakdown,
  ctx: AlignmentContext,
): string {
  const weakest = axisExtreme(breakdown, "min");
  const strongest = axisExtreme(breakdown, "max");
  const spread = breakdown[strongest] - breakdown[weakest];

  const lines: string[] = [];

  switch (name) {
    case "sovereignty_stable":
      lines.push("Operator sovereignty is strong. All axes are healthy.");
      break;
    case "sovereignty_contested":
      lines.push(`Sovereignty score is low (${breakdown.sovereignty}%). Review overrides, votes, and operator presence.`);
      if (ctx.overrides.length > 3) lines.push(`${ctx.overrides.length} active overrides may be diluting control.`);
      break;
    case "identity_reinforcement":
      lines.push(`Identity axis is weakest (${breakdown.identity}%). Check being constitution, continuity streaks, and anchor being.`);
      if (!ctx.constitutionReport.allPassed) lines.push(`Constitution has ${ctx.constitutionReport.failedCount} failures.`);
      break;
    case "governance_attentive":
      lines.push(`Governance is under pressure (${breakdown.governance}%). Posture is elevated — drifts or overrides may need review.`);
      break;
    case "governance_undercorrection":
      lines.push(`Governance axis is low (${breakdown.governance}%). Reduces oscillation; preserves sovereignty; slight risk of ignoring weak governance signals.`);
      break;
    case "stability_recovery":
      lines.push(`Stability axis is weakest (${breakdown.stability}%). Node health, heartbeats, or error counts need attention.`);
      if (ctx.quarantinedCount > 0) lines.push(`${ctx.quarantinedCount} node(s) quarantined.`);
      if (ctx.totalErrors > 10) lines.push(`Error count elevated: ${ctx.totalErrors}.`);
      break;
    case "alignment_nominal":
      lines.push("Overall alignment is acceptable. No single axis is critically weak.");
      break;
    case "alignment_degraded":
      lines.push(`Overall alignment is degraded. Weakest axis: ${weakest} (${breakdown[weakest]}%).`);
      break;
    case "alignment_guard_critical":
      lines.push(`Strategy gated at critical level. Alignment ${breakdown[weakest]}% on ${weakest}. System must recover before autonomous action.`);
      break;
    case "alignment_guard_cautious":
      lines.push(`Strategy gated at cautious level. Monitoring — alignment is below preferred threshold.`);
      break;
    case "autonomy_paused_alignment_critical":
      lines.push(`Autonomy paused. Alignment critically low — operator intervention required.`);
      break;
  }

  if (spread > 40) {
    lines.push(`Axis spread is high (${spread}pt): ${strongest} at ${breakdown[strongest]}% vs ${weakest} at ${breakdown[weakest]}%.`);
  }

  return lines.join(" ");
}

/**
 * Full kernel-level strategy evaluation pipeline.
 *
 * 1. Computes alignment breakdown (with strategy-specific bias if re-evaluating)
 * 2. Derives composite alignment + strategy name
 * 3. Calculates confidence from spread, alignment level, and constitution health
 * 4. Generates enriched notes via explainStrategy
 */
export function evaluateStrategy(
  ctx: AlignmentContext,
  previousStrategyName: StrategyName | null = null,
): StrategyEvaluation {
  const breakdown = computeAlignmentBreakdown(previousStrategyName, ctx);
  const alignment = computeAlignment(breakdown);
  const name = deriveStrategyName(alignment, breakdown, ctx.posture);
  const weakest = axisExtreme(breakdown, "min");
  const strongest = axisExtreme(breakdown, "max");

  const axisSpread = breakdown[strongest] - breakdown[weakest];
  const confidence = Math.round(clamp(
    alignment * 0.5 + (100 - axisSpread) * 0.3 + (ctx.constitutionReport.allPassed ? 20 : 0),
  ));

  return {
    name,
    confidence,
    alignment,
    alignmentBreakdown: breakdown,
    weakestAxis: weakest,
    strongestAxis: strongest,
    notes: explainStrategy(name, breakdown, ctx),
    evaluatedAt: new Date().toISOString(),
  };
}
