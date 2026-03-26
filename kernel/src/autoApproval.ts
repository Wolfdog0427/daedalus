/**
 * Auto-Approval Gate
 *
 * Multi-axis safety check for proposed alignment changes. A change
 * is auto-approved only when ALL conditions are met:
 *
 *   1. Alignment ≥ threshold (default 95)
 *   2. Confidence ≥ threshold (default 80)
 *   3. Derived impact is LOW
 *   4. No invariants touched
 *   5. Change is reversible
 *   6. Not in safe mode (unless config allows)
 *   7. Cooldown respected (rate limiting)
 *
 * Impact, invariant touch, and reversibility are DERIVED from the
 * proposal's kind and payload — not declared by the caller.
 */

import type {
  ChangeProposal,
  ChangeProposalKind,
  ChangeImpact,
  ApprovalDecision,
  ApprovalReasonBreakdown,
  ApprovalGateConfig,
  StrategyEvaluation,
  SafeModeState,
  AlignmentConfig,
  ChangeImpactInput,
} from "./types";
import { DEFAULT_APPROVAL_GATE_CONFIG } from "./types";
import { classifyChangeImpact, detectInvariantTouchBySurface } from "./changeClassifier";

let gateConfig: ApprovalGateConfig = { ...DEFAULT_APPROVAL_GATE_CONFIG };
let lastApprovalTimestamp = 0;
let recentDecisions: ApprovalDecision[] = [];

const MAX_DECISION_HISTORY = 50;

// ── Impact Classification ───────────────────────────────────────────

function classifyImpact(proposal: ChangeProposal, currentConfig?: AlignmentConfig): ChangeImpact {
  const { kind, payload } = proposal;

  switch (kind) {
    case "alignment_config": {
      const deltas = Object.entries(payload)
        .filter(([k]) => k.endsWith("Weight") || k === "alignmentFloor")
        .map(([k, v]) => {
          if (typeof v !== "number") return 0;
          if (k === "alignmentFloor") return Math.abs(v - (currentConfig?.alignmentFloor ?? 60)) / 100;
          const currentWeight = currentConfig ? (currentConfig as any)[k] ?? 0.25 : 0.25;
          return Math.abs(v - currentWeight);
        });
      const maxDelta = Math.max(0, ...deltas);
      if (maxDelta <= 0.05) return "low";
      if (maxDelta <= 0.15) return "medium";
      return "high";
    }
    case "kernel_config": {
      const sensitivity = payload.strategySensitivity as number | undefined;
      const strictness = payload.governanceStrictness as number | undefined;
      let maxDelta = 0;
      if (sensitivity != null) maxDelta = Math.max(maxDelta, Math.abs(sensitivity - 1.0));
      if (strictness != null) maxDelta = Math.max(maxDelta, Math.abs(strictness - 0.8));
      if (maxDelta <= 0.1) return "low";
      if (maxDelta <= 0.3) return "medium";
      return "high";
    }
    case "strategy_override":
      return "medium";
    case "posture_override":
      return "medium";
    case "safe_mode_toggle":
      return "high";
    case "governance_override": {
      const scope = payload.scope as string | undefined;
      if (scope === "GLOBAL") return "high";
      return "medium";
    }
    default:
      return "high";
  }
}

// ── Invariant Detection ─────────────────────────────────────────────

function detectInvariantTouch(proposal: ChangeProposal, currentConfig?: AlignmentConfig): boolean {
  const { kind, payload } = proposal;

  switch (kind) {
    case "alignment_config": {
      const weights = [
        payload.sovereigntyWeight ?? currentConfig?.sovereigntyWeight ?? 0.4,
        payload.identityWeight ?? currentConfig?.identityWeight ?? 0.2,
        payload.governanceWeight ?? currentConfig?.governanceWeight ?? 0.3,
        payload.stabilityWeight ?? currentConfig?.stabilityWeight ?? 0.1,
      ] as number[];
      const sum = weights.reduce((s, w) => s + w, 0);
      if (Math.abs(sum - 1.0) > 0.01) return true;

      const floor = (payload.alignmentFloor as number) ?? currentConfig?.alignmentFloor ?? 60;
      if (floor < 30 || floor > 99) return true;

      return false;
    }
    case "safe_mode_toggle":
      return true;
    case "governance_override": {
      const scope = payload.scope as string | undefined;
      const effect = payload.effect as string | undefined;
      if (scope === "GLOBAL" && effect === "DENY") return true;
      return false;
    }
    default:
      return false;
  }
}

// ── Reversibility Assessment ────────────────────────────────────────

function assessReversibility(proposal: ChangeProposal): boolean {
  switch (proposal.kind) {
    case "alignment_config":
    case "kernel_config":
    case "posture_override":
    case "strategy_override":
      return true;
    case "safe_mode_toggle":
      return true;
    case "governance_override": {
      const scope = proposal.payload.scope as string | undefined;
      return scope !== "GLOBAL";
    }
    default:
      return false;
  }
}

// ── Core Gate ───────────────────────────────────────────────────────

export function shouldAutoApprove(
  proposal: ChangeProposal,
  evaluation: StrategyEvaluation,
  safeMode: SafeModeState,
  currentAlignmentConfig?: AlignmentConfig,
  surfaceInput?: ChangeImpactInput,
  confidenceApprovalBias: number = 0,
): ApprovalDecision {
  const now = Date.now();

  let derivedImpact: ChangeImpact;
  let touchesInvariants: boolean;
  let reversible: boolean;

  if (surfaceInput) {
    const impactResult = classifyChangeImpact(surfaceInput);
    const invariantResult = detectInvariantTouchBySurface(surfaceInput.surfaces);
    derivedImpact = impactResult.impact;
    touchesInvariants = invariantResult.touchesInvariants;
    reversible = surfaceInput.reversible;
  } else {
    derivedImpact = classifyImpact(proposal, currentAlignmentConfig);
    touchesInvariants = detectInvariantTouch(proposal, currentAlignmentConfig);
    reversible = assessReversibility(proposal);
  }

  // System confidence biases the alignment threshold: high confidence
  // lowers it (more fluid), low confidence raises it (more cautious).
  // The bias only applies to LOW-impact, non-invariant, reversible changes.
  // The bias can reduce the threshold but never below 80 OR below the
  // operator's explicit configuration — whichever is lower.
  const biasableImpact = derivedImpact === "low" && !touchesInvariants && reversible;
  const maxBiasReduction = Math.max(0, gateConfig.alignmentThreshold - 80);
  const effectiveBias = biasableImpact ? Math.min(confidenceApprovalBias, maxBiasReduction) : 0;
  const effectiveAlignmentThreshold = gateConfig.alignmentThreshold - effectiveBias;

  const alignmentOK = evaluation.alignment >= effectiveAlignmentThreshold;
  const confidenceOK = evaluation.confidence >= gateConfig.confidenceThreshold;
  const impactOK = derivedImpact === "low";
  const invariantsOK = !touchesInvariants;
  const reversibleOK = reversible;
  const safeModeOK = !safeMode.active || gateConfig.allowDuringSafeMode;
  const cooldownOK = (now - lastApprovalTimestamp) >= gateConfig.cooldownMs;

  const autoApprove =
    alignmentOK &&
    confidenceOK &&
    impactOK &&
    invariantsOK &&
    reversibleOK &&
    safeModeOK &&
    cooldownOK;

  const reasons: ApprovalReasonBreakdown = {
    alignmentOK,
    confidenceOK,
    impactOK,
    invariantsOK,
    reversibleOK,
    safeModeOK,
    cooldownOK,
  };

  const decision: ApprovalDecision = {
    autoApprove,
    proposal,
    reasons,
    derivedImpact,
    touchesInvariants,
    reversible,
    alignment: evaluation.alignment,
    confidence: evaluation.confidence,
    decidedAt: now,
  };

  if (autoApprove) {
    lastApprovalTimestamp = now;
  }

  recentDecisions.push(decision);
  if (recentDecisions.length > MAX_DECISION_HISTORY) {
    recentDecisions = recentDecisions.slice(recentDecisions.length - MAX_DECISION_HISTORY);
  }

  return decision;
}

// ── Batch evaluation for tickKernel ─────────────────────────────────

export function evaluateProposals(
  proposals: ChangeProposal[],
  evaluation: StrategyEvaluation,
  safeMode: SafeModeState,
  currentAlignmentConfig?: AlignmentConfig,
  confidenceApprovalBias: number = 0,
): ApprovalDecision[] {
  return proposals.map(p =>
    shouldAutoApprove(p, evaluation, safeMode, currentAlignmentConfig, undefined, confidenceApprovalBias),
  );
}

// ── Config ──────────────────────────────────────────────────────────

export function getApprovalGateConfig(): ApprovalGateConfig {
  return { ...gateConfig };
}

export function updateApprovalGateConfig(patch: Partial<ApprovalGateConfig>): ApprovalGateConfig {
  gateConfig = { ...gateConfig, ...patch };
  return { ...gateConfig };
}

export function getRecentApprovalDecisions(): ApprovalDecision[] {
  return [...recentDecisions];
}

export function resetApprovalGate(): void {
  gateConfig = { ...DEFAULT_APPROVAL_GATE_CONFIG };
  lastApprovalTimestamp = 0;
  recentDecisions = [];
}

export { classifyImpact, detectInvariantTouch, assessReversibility };
