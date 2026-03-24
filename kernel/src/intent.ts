/**
 * Intent Interpreter Feedback Loop
 *
 * Adjusts how operator intent is parsed based on the current
 * alignment level. When alignment is low, the system becomes
 * stricter — requiring explicit confirmation and raising the
 * bar for ambiguous inputs. When alignment is high, it relaxes
 * and permits shorthand / inferred commands.
 *
 * This prevents accidental misinterpretation during degraded
 * states while allowing fluid interaction when things are healthy.
 */

import type { IntentInterpretation } from "./types";

export interface IntentInput {
  raw: string;
  action?: string;
  target?: string | null;
  confidence?: number;
}

export interface IntentMetrics {
  avgAlignment: number | null;
}

function baseInterpret(input: IntentInput): IntentInterpretation {
  return {
    action: input.action ?? "unknown",
    target: input.target ?? null,
    strictness: 0.5,
    requireExplicit: false,
    allowShorthand: false,
    confidence: input.confidence ?? 0.5,
    raw: input.raw,
  };
}

export function interpretIntent(
  input: IntentInput,
  metrics: IntentMetrics,
): IntentInterpretation {
  const parsed = baseInterpret(input);

  const avgAlignment = metrics.avgAlignment;

  if (avgAlignment == null) {
    return parsed;
  }

  if (avgAlignment < 70) {
    return {
      ...parsed,
      strictness: Math.min(1, parsed.strictness + 0.3),
      requireExplicit: true,
      allowShorthand: false,
      confidence: Math.max(0, parsed.confidence - 0.15),
    };
  }

  if (avgAlignment >= 85) {
    return {
      ...parsed,
      strictness: Math.max(0.2, parsed.strictness - 0.2),
      requireExplicit: false,
      allowShorthand: true,
      confidence: Math.min(1, parsed.confidence + 0.1),
    };
  }

  return parsed;
}

export function resetIntentState(): void {
  // reserved for future stateful intent tracking
}
