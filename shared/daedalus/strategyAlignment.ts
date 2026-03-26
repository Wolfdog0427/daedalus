/**
 * Strategy Alignment — the four-axis evaluation of system health.
 *
 * Alignment is not a boolean. It is a weighted composite of four
 * orthogonal axes that together answer: "Is Daedalus doing what
 * it was built to do, for the operator who built it?"
 *
 * Axes:
 *   Sovereignty  — Is the operator in control? Are overrides respected?
 *   Identity     — Is the being constitution intact? Is continuity healthy?
 *   Governance   — Is posture appropriate? Are drifts contained?
 *   Stability    — Are nodes alive? Is the fabric under pressure?
 *
 * Each axis produces a 0–100 score. The composite alignment is a
 * weighted blend. Strategy names are derived from the dominant axis
 * and overall alignment level.
 */

import type {
  PostureState,
  BeingPresenceDetail,
  GovernanceOverride,
  ContinuityDrift,
  BeingVote,
} from "./contracts";
import type { BeingInvariantReport } from "./beingConstitution";
import { ANCHOR_STREAK_MINIMUM } from "./beingConstitution";

// ── Types ─────────────────────────────────────────────────────────────

export interface AlignmentBreakdown {
  sovereignty: number;
  identity: number;
  governance: number;
  stability: number;
}

export interface AlignmentWeights {
  sovereignty: number;
  identity: number;
  governance: number;
  stability: number;
}

export type StrategyName =
  | "sovereignty_stable"
  | "sovereignty_contested"
  | "identity_reinforcement"
  | "governance_attentive"
  | "governance_undercorrection"
  | "stability_recovery"
  | "alignment_nominal"
  | "alignment_degraded";

export interface StrategyEvaluation {
  name: StrategyName;
  confidence: number;
  alignment: number;
  alignmentBreakdown: AlignmentBreakdown;
  weakestAxis: keyof AlignmentBreakdown;
  strongestAxis: keyof AlignmentBreakdown;
  notes: string;
  evaluatedAt: string;
}

export interface AlignmentContext {
  beings: BeingPresenceDetail[];
  constitutionReport: BeingInvariantReport;
  posture: PostureState;
  postureReason: string;
  overrides: GovernanceOverride[];
  drifts: ContinuityDrift[];
  votes: BeingVote[];
  nodeCount: number;
  quarantinedCount: number;
  totalErrors: number;
  activeHeartbeats: number;
}

// ── Weights ───────────────────────────────────────────────────────────

export const DEFAULT_ALIGNMENT_WEIGHTS: Readonly<AlignmentWeights> = Object.freeze({
  sovereignty: 0.4,
  identity: 0.2,
  governance: 0.3,
  stability: 0.1,
});

// ── Axis Scorers ──────────────────────────────────────────────────────

function clamp(v: number, min = 0, max = 100): number {
  return Math.min(max, Math.max(min, v));
}

export function scoreSovereignty(ctx: AlignmentContext): number {
  let score = 0;
  const operator = ctx.beings.find(b => b.id === "operator");

  if (operator) {
    score += 30;
    if (operator.presenceMode === "active" || operator.presenceMode === "dominant") score += 15;
    if (operator.isGuiding) score += 10;
    score += Math.round(operator.influenceLevel * 20);
  } else if (ctx.beings.length === 0) {
    // L3: Autonomous preservation — operator absent but constitutional governance intact
    if (ctx.constitutionReport.allPassed && ctx.posture !== "LOCKDOWN") score += 15;
  }

  const hasGlobalDeny = ctx.overrides.some(o => o.scope === "GLOBAL" && o.effect === "DENY");
  if (hasGlobalDeny) score -= 30;
  if (ctx.posture === "LOCKDOWN") score -= 15;

  const denyWeight = ctx.votes.filter(v => v.vote === "DENY").reduce((s, v) => s + v.weight, 0);
  const totalWeight = ctx.votes.reduce((s, v) => s + v.weight, 0);
  if (totalWeight > 0 && denyWeight / totalWeight > 0.5) score -= 20;

  if (ctx.beings.length > 0) {
    const maxInfluence = Math.max(...ctx.beings.map(b => b.influenceLevel));
    if (operator && operator.influenceLevel >= maxInfluence) score += 10;
  }

  return clamp(score);
}

export function scoreIdentity(ctx: AlignmentContext): number {
  let score = 0;

  if (ctx.constitutionReport.allPassed) {
    score += 45;
  } else {
    const passRate = 1 - ctx.constitutionReport.failedCount / Math.max(1, ctx.constitutionReport.checks.length);
    score += Math.round(passRate * 30);
  }

  if (ctx.beings.length > 0) {
    score += 15;
    const healthyFraction = ctx.beings.filter(b => b.continuity.healthy).length / ctx.beings.length;
    score += Math.round(healthyFraction * 20);

    const maxStreak = Math.max(...ctx.beings.map(b => b.continuity.streak));
    if (maxStreak >= ANCHOR_STREAK_MINIMUM) score += 15;
    else if (maxStreak > 0) score += 5;
  }

  return clamp(score);
}

export function scoreGovernance(ctx: AlignmentContext): number {
  let score = 50;

  if (ctx.posture === "OPEN") score += 25;
  else if (ctx.posture === "ATTENTIVE") score += 10;
  else if (ctx.posture === "GUARDED") score -= 10;
  else if (ctx.posture === "LOCKDOWN") score -= 25;

  const highDrifts = ctx.drifts.filter(d => d.severity === "HIGH").length;
  const medDrifts = ctx.drifts.filter(d => d.severity === "MEDIUM").length;
  score -= highDrifts * 15;
  score -= medDrifts * 5;

  if (ctx.overrides.length > 10) score -= 10;
  else if (ctx.overrides.length === 0 && ctx.posture === "OPEN") score += 10;

  if (ctx.constitutionReport.allPassed) score += 10;

  return clamp(score);
}

export function scoreStability(ctx: AlignmentContext): number {
  let score = 0;

  if (ctx.nodeCount > 0) {
    score += 20;
    const healthyFraction = Math.max(0, ctx.nodeCount - ctx.quarantinedCount) / ctx.nodeCount;
    score += Math.round(healthyFraction * 30);

    if (ctx.activeHeartbeats > 0) {
      const heartbeatFraction = ctx.activeHeartbeats / ctx.nodeCount;
      score += Math.round(heartbeatFraction * 25);
    }

    if (ctx.totalErrors === 0) score += 15;
    else if (ctx.totalErrors <= 5) score += 10;
    else if (ctx.totalErrors <= 20) score += 5;
  } else {
    // L2: Zero nodes = minimal stability, not 50. System with no nodes shouldn't
    // report moderate stability.
    score += 5;
  }

  if (ctx.quarantinedCount === 0) score += 10;

  return clamp(score);
}

// ── Composite ─────────────────────────────────────────────────────────

export function computeAlignment(
  breakdown: AlignmentBreakdown,
  weights: AlignmentWeights = DEFAULT_ALIGNMENT_WEIGHTS,
): number {
  const score =
    breakdown.sovereignty * weights.sovereignty +
    breakdown.identity * weights.identity +
    breakdown.governance * weights.governance +
    breakdown.stability * weights.stability;

  return Math.round(clamp(score));
}

export function computeAlignmentBreakdown(ctx: AlignmentContext): AlignmentBreakdown {
  return {
    sovereignty: scoreSovereignty(ctx),
    identity: scoreIdentity(ctx),
    governance: scoreGovernance(ctx),
    stability: scoreStability(ctx),
  };
}

// ── Strategy Derivation ───────────────────────────────────────────────

function axisExtreme(b: AlignmentBreakdown, pick: "min" | "max"): keyof AlignmentBreakdown {
  const entries = Object.entries(b) as [keyof AlignmentBreakdown, number][];
  return entries.reduce((best, [k, v]) => {
    const cmp = pick === "min" ? v < best[1] : v > best[1];
    return cmp ? [k, v] : best;
  }, entries[0])[0];
}

export function deriveStrategyName(
  alignment: number,
  breakdown: AlignmentBreakdown,
  posture: PostureState,
): StrategyName {
  const weakest = axisExtreme(breakdown, "min");

  if (alignment >= 80) {
    if (breakdown.sovereignty >= 80) return "sovereignty_stable";
    return "alignment_nominal";
  }

  if (alignment >= 60) {
    if (weakest === "governance" && (posture === "ATTENTIVE" || posture === "GUARDED")) {
      return "governance_attentive";
    }
    if (weakest === "governance") return "governance_undercorrection";
    if (weakest === "identity") return "identity_reinforcement";
    if (weakest === "sovereignty") return "sovereignty_contested";
    if (weakest === "stability") return "stability_recovery";
    return "alignment_nominal";
  }

  if (alignment >= 40) {
    if (weakest === "stability") return "stability_recovery";
    if (weakest === "sovereignty") return "sovereignty_contested";
    if (weakest === "governance") return "governance_undercorrection";
    if (weakest === "identity") return "identity_reinforcement";
    return "alignment_degraded";
  }

  return "alignment_degraded";
}

function strategyNotes(name: StrategyName, breakdown: AlignmentBreakdown): string {
  switch (name) {
    case "sovereignty_stable":
      return "Operator sovereignty is strong. All axes are healthy.";
    case "sovereignty_contested":
      return `Sovereignty score is low (${breakdown.sovereignty}%). Review overrides, votes, and operator presence.`;
    case "identity_reinforcement":
      return `Identity axis is weakest (${breakdown.identity}%). Check being constitution, continuity streaks, and anchor being.`;
    case "governance_attentive":
      return `Governance is under pressure (${breakdown.governance}%). Posture is elevated — drifts or overrides may need review.`;
    case "governance_undercorrection":
      return `Governance axis is low (${breakdown.governance}%). Reduces oscillation; preserves sovereignty; slight risk of ignoring weak governance signals.`;
    case "stability_recovery":
      return `Stability axis is weakest (${breakdown.stability}%). Node health, heartbeats, or error counts need attention.`;
    case "alignment_nominal":
      return "Overall alignment is acceptable. No single axis is critically weak.";
    case "alignment_degraded":
      return `Overall alignment is degraded. Weakest axis: ${axisExtreme(breakdown, "min")} (${breakdown[axisExtreme(breakdown, "min")]}%).`;
  }
}

// ── Full Evaluation ───────────────────────────────────────────────────

export function evaluateStrategy(ctx: AlignmentContext): StrategyEvaluation {
  const breakdown = computeAlignmentBreakdown(ctx);
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
    notes: strategyNotes(name, breakdown),
    evaluatedAt: new Date().toISOString(),
  };
}
