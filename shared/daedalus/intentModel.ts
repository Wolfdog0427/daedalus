/** Feature toggle: set to false to disable intent modeling. */
export const INTENT_MODEL_ENABLED = true;

export type OperatorIntent = "task" | "exploration" | "idle" | "transition";

export type IntentSignalType = "input" | "navigation" | "focus" | "idle";

export interface IntentSignal {
  timestamp: number;
  type: IntentSignalType;
}

export interface IntentModelConfig {
  windowMs: number;
  minSignals: number;
  proposalIntervalMs: number;
}

export const INTENT_MODEL_DEFAULTS: IntentModelConfig = {
  windowMs: 8000,
  minSignals: 4,
  proposalIntervalMs: 10000,
};

export interface IntentSnapshot {
  currentIntent: OperatorIntent | null;
  signalCount: number;
}
