/** Feature toggle: set to false to disable meta-strategy layer. */
export const META_STRATEGY_ENABLED = true;

import type { ExpressiveStrategy } from "./expressiveStrategy";

export type MetaStrategy =
  | "stability-cycle"
  | "responsiveness-cycle"
  | "exploration-cycle"
  | "cooldown-cycle"
  | "mixed-cycle";

export interface StrategyHistoryEntry {
  strategy: ExpressiveStrategy;
  timestamp: number;
}

/**
 * Internal evaluation state — tracks the candidate meta-strategy,
 * accumulated confidence, and a rolling window of Tier-3 strategy
 * decisions that inform the meta-level inference.
 */
export interface MetaStrategyEvalState {
  candidate: MetaStrategy | null;
  confidence: number;
  lastEvalAt: number;
  history: StrategyHistoryEntry[];
}

export const META_STRATEGY_EVAL_IDLE: MetaStrategyEvalState = {
  candidate: null,
  confidence: 0,
  lastEvalAt: 0,
  history: [],
};

export interface MetaStrategyConfig {
  minConfidence: number;
  reinforceStep: number;
  weakenStep: number;
  decayStep: number;
  decayAfterMs: number;
  proposalIntervalMs: number;
  historyWindowMs: number;
  minHistoryEntries: number;
}

export const META_STRATEGY_DEFAULTS: MetaStrategyConfig = {
  minConfidence: 0.65,
  reinforceStep: 0.12,
  weakenStep: 0.1,
  decayStep: 0.15,
  decayAfterMs: 30000,
  proposalIntervalMs: 20000,
  historyWindowMs: 60000,
  minHistoryEntries: 3,
};
