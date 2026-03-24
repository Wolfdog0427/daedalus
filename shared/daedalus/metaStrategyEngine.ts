import type { ExpressiveStrategy } from "./expressiveStrategy";
import type { AnalyticsSnapshot } from "./sceneAnalytics";
import type { AdaptationTuning } from "./sceneAdaptation";
import type { AutonomyProposal } from "./sceneAutonomy";
import type {
  MetaStrategy,
  StrategyHistoryEntry,
  MetaStrategyEvalState,
  MetaStrategyConfig,
} from "./metaStrategy";
import { META_STRATEGY_DEFAULTS } from "./metaStrategy";

/** Remove history entries older than the analysis window. */
export function trimHistory(
  history: StrategyHistoryEntry[],
  windowMs: number,
  now: number = Date.now(),
): StrategyHistoryEntry[] {
  const cutoff = now - windowMs;
  return history.filter((h) => h.timestamp >= cutoff);
}

/** Add an entry and trim to window. */
export function recordStrategy(
  history: StrategyHistoryEntry[],
  strategy: ExpressiveStrategy,
  windowMs: number,
  now: number = Date.now(),
): StrategyHistoryEntry[] {
  return trimHistory([...history, { strategy, timestamp: now }], windowMs, now);
}

/**
 * Count occurrences of each strategy in the history window.
 */
function countStrategies(
  history: StrategyHistoryEntry[],
): Partial<Record<ExpressiveStrategy, number>> {
  const counts: Partial<Record<ExpressiveStrategy, number>> = {};
  for (const h of history) {
    counts[h.strategy] = (counts[h.strategy] ?? 0) + 1;
  }
  return counts;
}

/**
 * Infer the appropriate meta-strategy from the distribution
 * of recent Tier-3 strategy decisions and current analytics.
 *
 * Returns null when there aren't enough history entries.
 */
export function inferMetaStrategy(
  history: StrategyHistoryEntry[],
  analytics: AnalyticsSnapshot,
  config: MetaStrategyConfig = META_STRATEGY_DEFAULTS,
): MetaStrategy | null {
  if (history.length < config.minHistoryEntries) return null;

  const counts = countStrategies(history);
  const total = history.length;
  const dominant = Object.entries(counts).reduce(
    (best, [s, c]) => (c! > best[1] ? [s, c!] : best),
    ["", 0] as [string, number],
  );

  const dominantStrategy = dominant[0] as ExpressiveStrategy;
  const dominantRatio = dominant[1] / total;

  // Strong pattern: >50% of decisions are the same strategy
  if (dominantRatio > 0.5) {
    if (dominantStrategy === "sustained-focus" || dominantStrategy === "stability-first")
      return "stability-cycle";
    if (dominantStrategy === "broad-exploration")
      return "exploration-cycle";
    if (dominantStrategy === "cooldown-arc")
      return "cooldown-cycle";
    if (dominantStrategy === "responsiveness-first")
      return "responsiveness-cycle";
  }

  // Analytics-driven fallbacks
  if (analytics.expressiveHealth > 0.85)
    return "responsiveness-cycle";
  if (analytics.expressiveHealth < 0.4)
    return "cooldown-cycle";

  // No clear dominant → mixed
  if (total >= config.minHistoryEntries)
    return "mixed-cycle";

  return null;
}

/**
 * Map a meta-strategy to bounded, safe tuning overrides.
 */
export function recommendForMetaStrategy(meta: MetaStrategy): AdaptationTuning {
  switch (meta) {
    case "stability-cycle":
      return {
        timelineMomentumHalfLifeMs: 11000,
        grammarDefaultBlendMs: 750,
        grammarDefaultDwellMs: 1300,
      };
    case "exploration-cycle":
      return {
        timelineMomentumHalfLifeMs: 4500,
        narrativeMinIntervalMs: 2400,
      };
    case "cooldown-cycle":
      return {
        governorCooldownMs: 1700,
        governorEscalationLockMs: 4500,
        narrativeMinIntervalMs: 7000,
        grammarDefaultBlendMs: 700,
      };
    case "responsiveness-cycle":
      return {
        governorCooldownMs: 600,
        grammarDefaultBlendMs: 320,
      };
    case "mixed-cycle":
      return {
        grammarDefaultBlendMs: 500,
      };
  }
}

/**
 * Evolve meta-strategy evaluation state based on the currently
 * inferred meta-strategy. Builds confidence when the same
 * meta-strategy is repeatedly inferred, weakens otherwise.
 */
export function evolveMetaStrategy(
  prev: MetaStrategyEvalState,
  analytics: AnalyticsSnapshot,
  config: MetaStrategyConfig = META_STRATEGY_DEFAULTS,
  now: number = Date.now(),
): MetaStrategyEvalState {
  const trimmed = trimHistory(prev.history, config.historyWindowMs, now);
  let { confidence } = prev;

  // Time-based decay
  if (prev.lastEvalAt > 0 && now - prev.lastEvalAt > config.decayAfterMs) {
    confidence = Math.max(0, confidence - config.decayStep);
  }

  const inferred = inferMetaStrategy(trimmed, analytics, config);

  if (inferred === null) {
    return {
      ...prev,
      history: trimmed,
      confidence: Math.max(0, confidence - config.weakenStep),
      lastEvalAt: now,
    };
  }

  if (inferred === prev.candidate) {
    return {
      candidate: inferred,
      confidence: Math.min(1, confidence + config.reinforceStep),
      lastEvalAt: now,
      history: trimmed,
    };
  }

  // New candidate
  return {
    candidate: inferred,
    confidence: config.reinforceStep,
    lastEvalAt: now,
    history: trimmed,
  };
}

/**
 * Full evaluation pipeline: evolves state and produces a proposal
 * when confidence exceeds threshold and rate limit has elapsed.
 */
export function evaluateMetaStrategy(
  state: MetaStrategyEvalState,
  analytics: AnalyticsSnapshot,
  lastProposalAt: number,
  nextId: number,
  config: MetaStrategyConfig = META_STRATEGY_DEFAULTS,
  now: number = Date.now(),
): { state: MetaStrategyEvalState; proposal: AutonomyProposal | null } {
  const nextState = evolveMetaStrategy(state, analytics, config, now);

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
      reason: `Meta-strategy: ${nextState.candidate} (${(nextState.confidence * 100).toFixed(0)}% confidence)`,
      recommended: recommendForMetaStrategy(nextState.candidate),
    },
  };
}
