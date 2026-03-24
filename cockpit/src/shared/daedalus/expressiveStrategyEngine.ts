import type { OperatorIntent } from "./intentModel";
import type { AnalyticsSnapshot } from "./sceneAnalytics";
import type { AdaptationTuning } from "./sceneAdaptation";
import type { AutonomyProposal } from "./sceneAutonomy";
import type {
  ExpressiveStrategy,
  StrategyEvalState,
  StrategyConfig,
} from "./expressiveStrategy";
import { STRATEGY_DEFAULTS, STRATEGY_EVAL_IDLE } from "./expressiveStrategy";

/**
 * Infer the best-fit long-arc strategy from current operator intent
 * and system analytics. Returns null when no clear strategy applies.
 *
 * Priority order: stability → health protection → intent-specific → optimization.
 */
export function inferStrategy(
  intent: OperatorIntent | null,
  analytics: AnalyticsSnapshot,
): ExpressiveStrategy | null {
  // Safety: rough transitions + frequent rejections → stabilize
  if (analytics.transitionSmoothness < 0.5 && analytics.grammarRejectionRate > 0.3)
    return "stability-first";

  // Health protection: system is struggling
  if (analytics.expressiveHealth < 0.4)
    return "cooldown-arc";

  // Intent-specific strategies
  if (intent === "task" && analytics.sceneStability > 0.7)
    return "sustained-focus";

  if (intent === "exploration" && analytics.momentumVolatility < 0.4)
    return "broad-exploration";

  if (intent === "transition")
    return "transition-arc";

  if (intent === "idle" && analytics.expressiveHealth < 0.6)
    return "cooldown-arc";

  // Optimization: everything is healthy → be more responsive
  if (analytics.expressiveHealth > 0.85)
    return "responsiveness-first";

  return null;
}

/**
 * Map a strategy to bounded, safe tuning overrides.
 */
export function recommendForStrategy(strategy: ExpressiveStrategy): AdaptationTuning {
  switch (strategy) {
    case "sustained-focus":
      return {
        governorCooldownMs: 600,
        grammarDefaultBlendMs: 300,
      };
    case "broad-exploration":
      return {
        timelineMomentumHalfLifeMs: 4500,
        narrativeMinIntervalMs: 2200,
      };
    case "cooldown-arc":
      return {
        governorCooldownMs: 1600,
        governorEscalationLockMs: 4000,
        narrativeMinIntervalMs: 6500,
        grammarDefaultBlendMs: 700,
      };
    case "transition-arc":
      return {
        grammarDefaultBlendMs: 450,
      };
    case "stability-first":
      return {
        timelineMomentumHalfLifeMs: 10000,
        grammarDefaultBlendMs: 700,
        grammarDefaultDwellMs: 1400,
      };
    case "responsiveness-first":
      return {
        governorCooldownMs: 650,
        grammarDefaultBlendMs: 350,
      };
  }
}

/**
 * Evolve strategy evaluation state based on the currently inferred
 * strategy. Builds confidence when the same strategy is repeatedly
 * inferred, weakens when it changes, and decays over time.
 */
export function evolveStrategy(
  prev: StrategyEvalState,
  intent: OperatorIntent | null,
  analytics: AnalyticsSnapshot,
  config: StrategyConfig = STRATEGY_DEFAULTS,
  now: number = Date.now(),
): StrategyEvalState {
  let { confidence } = prev;

  // Time-based decay: if too long since last evaluation, weaken
  if (prev.lastEvalAt > 0 && now - prev.lastEvalAt > config.decayAfterMs) {
    confidence = Math.max(0, confidence - config.decayStep);
  }

  const inferred = inferStrategy(intent, analytics);

  if (inferred === null) {
    return {
      ...prev,
      confidence: Math.max(0, confidence - config.weakenStep),
      lastEvalAt: now,
    };
  }

  if (inferred === prev.candidate) {
    return {
      candidate: inferred,
      confidence: Math.min(1, confidence + config.reinforceStep),
      lastEvalAt: now,
    };
  }

  // New candidate — start building from a base step
  return {
    candidate: inferred,
    confidence: config.reinforceStep,
    lastEvalAt: now,
  };
}

/**
 * Full evaluation pipeline: evolves state and produces a proposal
 * when confidence exceeds the threshold and the rate limit has elapsed.
 */
export function evaluateStrategy(
  state: StrategyEvalState,
  intent: OperatorIntent | null,
  analytics: AnalyticsSnapshot,
  lastProposalAt: number,
  nextId: number,
  config: StrategyConfig = STRATEGY_DEFAULTS,
  now: number = Date.now(),
): { state: StrategyEvalState; proposal: AutonomyProposal | null } {
  const nextState = evolveStrategy(state, intent, analytics, config, now);

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
      reason: `Strategy: ${nextState.candidate} (${(nextState.confidence * 100).toFixed(0)}% confidence)`,
      recommended: recommendForStrategy(nextState.candidate),
    },
  };
}
