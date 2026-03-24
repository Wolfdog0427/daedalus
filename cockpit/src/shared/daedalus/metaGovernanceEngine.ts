import type { AnalyticsSnapshot } from "./sceneAnalytics";
import type { ExpressiveStrategy } from "./expressiveStrategy";
import type { MetaStrategy } from "./metaStrategy";
import type { AdaptationTuning } from "./sceneAdaptation";
import type { AutonomyProposal } from "./sceneAutonomy";
import type {
  MetaGovernanceIssue,
  MetaGovernanceEvalState,
  MetaGovernanceConfig,
} from "./metaGovernance";
import { META_GOVERNANCE_DEFAULTS } from "./metaGovernance";

/**
 * Detect systemic expressive issues by examining analytics,
 * the active Tier-3 strategy, and the active Tier-4 meta-strategy.
 *
 * Priority: hard instability > health extremes > cross-tier conflict > governor imbalance.
 */
export function detectIssue(
  analytics: AnalyticsSnapshot,
  activeStrategy: ExpressiveStrategy | null,
  activeMeta: MetaStrategy | null,
): MetaGovernanceIssue | null {
  // Hard instabilities
  if (analytics.momentumVolatility > 0.7)
    return "timeline-instability";
  if (analytics.grammarRejectionRate > 2)
    return "grammar-instability";
  if (analytics.narrativeDensity > 5)
    return "narrative-overdensity";

  // Health extremes (the system is either over- or under-tuned)
  if (analytics.expressiveHealth < 0.3)
    return "overcorrection";

  // Governor overworking
  if (analytics.governorInterventionRate > 3)
    return "governor-imbalance";

  // Cross-tier conflict: strategy and meta-strategy are pulling
  // in opposite directions
  if (activeStrategy && activeMeta) {
    const conflicting =
      (activeStrategy === "sustained-focus" && activeMeta === "exploration-cycle") ||
      (activeStrategy === "broad-exploration" && activeMeta === "stability-cycle") ||
      (activeStrategy === "cooldown-arc" && activeMeta === "responsiveness-cycle") ||
      (activeStrategy === "responsiveness-first" && activeMeta === "cooldown-cycle");
    if (conflicting) return "strategy-conflict";
  }

  // Healthy system being under-tuned — room for more responsiveness
  if (analytics.expressiveHealth > 0.92)
    return "undercorrection";

  return null;
}

/**
 * Map a governance issue to bounded, safe tuning overrides.
 */
export function recommendForIssue(issue: MetaGovernanceIssue): AdaptationTuning {
  switch (issue) {
    case "timeline-instability":
      return {
        timelineMomentumHalfLifeMs: 13000,
        grammarDefaultBlendMs: 750,
      };
    case "grammar-instability":
      return {
        grammarDefaultDwellMs: 1600,
        grammarDefaultBlendMs: 800,
      };
    case "narrative-overdensity":
      return {
        narrativeMinIntervalMs: 7000,
      };
    case "overcorrection":
      return {
        governorCooldownMs: 800,
        governorEscalationLockMs: 3000,
        grammarDefaultBlendMs: 450,
      };
    case "undercorrection":
      return {
        governorCooldownMs: 550,
        grammarDefaultBlendMs: 300,
      };
    case "strategy-conflict":
      return {
        grammarDefaultBlendMs: 600,
        timelineMomentumHalfLifeMs: 8000,
      };
    case "governor-imbalance":
      return {
        governorCooldownMs: 1200,
        governorEscalationLockMs: 3800,
      };
  }
}

/**
 * Evolve meta-governance evaluation state. Builds confidence
 * when the same issue is repeatedly detected, weakens when
 * the issue changes, and decays over time.
 */
export function evolveGovernance(
  prev: MetaGovernanceEvalState,
  analytics: AnalyticsSnapshot,
  activeStrategy: ExpressiveStrategy | null,
  activeMeta: MetaStrategy | null,
  config: MetaGovernanceConfig = META_GOVERNANCE_DEFAULTS,
  now: number = Date.now(),
): MetaGovernanceEvalState {
  let { confidence } = prev;

  // Time-based decay
  if (prev.lastEvalAt > 0 && now - prev.lastEvalAt > config.decayAfterMs) {
    confidence = Math.max(0, confidence - config.decayStep);
  }

  const issue = detectIssue(analytics, activeStrategy, activeMeta);

  if (issue === null) {
    return {
      ...prev,
      confidence: Math.max(0, confidence - config.weakenStep),
      lastEvalAt: now,
    };
  }

  if (issue === prev.candidate) {
    return {
      candidate: issue,
      confidence: Math.min(1, confidence + config.reinforceStep),
      lastEvalAt: now,
    };
  }

  // New issue — start building from base step
  return {
    candidate: issue,
    confidence: config.reinforceStep,
    lastEvalAt: now,
  };
}

/**
 * Full evaluation pipeline: evolves state and produces a proposal
 * when confidence exceeds threshold and rate limit has elapsed.
 */
export function evaluateGovernance(
  state: MetaGovernanceEvalState,
  analytics: AnalyticsSnapshot,
  activeStrategy: ExpressiveStrategy | null,
  activeMeta: MetaStrategy | null,
  lastProposalAt: number,
  nextId: number,
  config: MetaGovernanceConfig = META_GOVERNANCE_DEFAULTS,
  now: number = Date.now(),
): { state: MetaGovernanceEvalState; proposal: AutonomyProposal | null } {
  const nextState = evolveGovernance(
    state, analytics, activeStrategy, activeMeta, config, now,
  );

  if (!nextState.candidate)
    return { state: nextState, proposal: null };

  if (nextState.confidence < config.minConfidence)
    return { state: nextState, proposal: null };

  if (now - lastProposalAt < config.proposalIntervalMs)
    return { state: nextState, proposal: null };

  return {
    state: nextState,
    proposal: {
      id: nextId,
      timestamp: now,
      reason: `Governance: ${nextState.candidate} (${(nextState.confidence * 100).toFixed(0)}% confidence)`,
      recommended: recommendForIssue(nextState.candidate),
    },
  };
}
