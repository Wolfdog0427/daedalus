import type { IntentSignal, OperatorIntent, IntentModelConfig } from "./intentModel";
import { INTENT_MODEL_DEFAULTS } from "./intentModel";
import type { AdaptationTuning } from "./sceneAdaptation";
import type { AutonomyProposal } from "./sceneAutonomy";

/** Remove signals older than the analysis window. */
export function trimSignals(
  signals: IntentSignal[],
  windowMs: number,
  now: number = Date.now(),
): IntentSignal[] {
  const cutoff = now - windowMs;
  return signals.filter((s) => s.timestamp >= cutoff);
}

/**
 * Determine the operator's current interaction mode from signal
 * distribution within the window.
 *
 * Returns null when there are fewer signals than `minSignals`.
 */
export function inferIntent(
  signals: IntentSignal[],
  config: IntentModelConfig = INTENT_MODEL_DEFAULTS,
): OperatorIntent | null {
  if (signals.length < config.minSignals) return null;

  const counts = { input: 0, navigation: 0, focus: 0, idle: 0 };
  for (const s of signals) counts[s.type]++;

  if (counts.idle > signals.length * 0.6) return "idle";
  if (counts.input + counts.focus > counts.navigation * 2) return "task";
  if (counts.navigation > counts.input) return "exploration";
  return "transition";
}

/**
 * Map an operator intent to a safe, bounded set of tuning
 * overrides suited to that interaction mode.
 */
export function recommendForIntent(intent: OperatorIntent): AdaptationTuning {
  switch (intent) {
    case "task":
      return {
        governorCooldownMs: 700,
        grammarDefaultBlendMs: 350,
      };
    case "exploration":
      return {
        timelineMomentumHalfLifeMs: 5000,
        narrativeMinIntervalMs: 2500,
      };
    case "idle":
      return {
        governorCooldownMs: 1500,
        narrativeMinIntervalMs: 6000,
        grammarDefaultBlendMs: 700,
      };
    case "transition":
      return {
        grammarDefaultBlendMs: 500,
      };
  }
}

/**
 * Full evaluation pipeline: trims signals, infers intent, and
 * produces a proposal if warranted. Returns null when rate-limited
 * or when no clear intent can be determined.
 */
export function evaluateIntent(
  signals: IntentSignal[],
  lastProposalAt: number,
  nextId: number,
  config: IntentModelConfig = INTENT_MODEL_DEFAULTS,
  now: number = Date.now(),
): { intent: OperatorIntent; proposal: AutonomyProposal } | null {
  if (now - lastProposalAt < config.proposalIntervalMs) return null;

  const windowed = trimSignals(signals, config.windowMs, now);
  const intent = inferIntent(windowed, config);
  if (!intent) return null;

  const recommended = recommendForIntent(intent);

  return {
    intent,
    proposal: {
      id: nextId,
      timestamp: now,
      reason: `Operator intent: ${intent}`,
      recommended,
    },
  };
}
