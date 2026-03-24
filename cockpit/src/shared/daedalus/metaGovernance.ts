/** Feature toggle: set to false to disable meta-governance layer. */
export const META_GOVERNANCE_ENABLED = true;

export type MetaGovernanceIssue =
  | "overcorrection"
  | "undercorrection"
  | "strategy-conflict"
  | "timeline-instability"
  | "grammar-instability"
  | "governor-imbalance"
  | "narrative-overdensity";

/**
 * Internal evaluation state — tracks the candidate issue,
 * accumulated confidence, and last evaluation time.
 */
export interface MetaGovernanceEvalState {
  candidate: MetaGovernanceIssue | null;
  confidence: number;
  lastEvalAt: number;
}

export const META_GOVERNANCE_EVAL_IDLE: MetaGovernanceEvalState = {
  candidate: null,
  confidence: 0,
  lastEvalAt: 0,
};

export interface MetaGovernanceConfig {
  minConfidence: number;
  reinforceStep: number;
  weakenStep: number;
  decayStep: number;
  decayAfterMs: number;
  proposalIntervalMs: number;
}

export const META_GOVERNANCE_DEFAULTS: MetaGovernanceConfig = {
  minConfidence: 0.6,
  reinforceStep: 0.15,
  weakenStep: 0.1,
  decayStep: 0.18,
  decayAfterMs: 25000,
  proposalIntervalMs: 20000,
};
