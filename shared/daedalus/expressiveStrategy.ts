/** Feature toggle: set to false to disable strategy layer. */
export const STRATEGY_ENABLED = true;

export type ExpressiveStrategy =
  | "sustained-focus"
  | "broad-exploration"
  | "cooldown-arc"
  | "transition-arc"
  | "stability-first"
  | "responsiveness-first";

/**
 * Internal evaluation state — tracks the candidate strategy and
 * the confidence accumulating toward it over successive evaluations.
 */
export interface StrategyEvalState {
  candidate: ExpressiveStrategy | null;
  confidence: number;
  lastEvalAt: number;
}

export const STRATEGY_EVAL_IDLE: StrategyEvalState = {
  candidate: null,
  confidence: 0,
  lastEvalAt: 0,
};

export interface StrategyConfig {
  minConfidence: number;
  reinforceStep: number;
  weakenStep: number;
  decayStep: number;
  decayAfterMs: number;
  proposalIntervalMs: number;
}

export const STRATEGY_DEFAULTS: StrategyConfig = {
  minConfidence: 0.6,
  reinforceStep: 0.15,
  weakenStep: 0.1,
  decayStep: 0.2,
  decayAfterMs: 20000,
  proposalIntervalMs: 15000,
};
