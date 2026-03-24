/**
 * Kernel Multi-Strategy Dispatcher
 *
 * Full pipeline:
 *   1. Evaluate strategy via kernel strategy evaluator
 *   2. Gate the evaluation by alignment level
 *   3. Compute escalation level
 *   4. Update safe mode state
 *   5. Push alignment event (floor_breached / low / stable)
 *   6. If critical escalation → override to autonomy_paused
 *   7. Record in telemetry buffer
 *   8. Return the final evaluation
 */

import { evaluateStrategy } from "./strategy";
import { gateStrategyByAlignment } from "./strategyGate";
import { computeAlignmentEscalation } from "./escalation";
import { updateSafeModeFromAlignment } from "./safeMode";
import { kernelTelemetry } from "./telemetry";
import type {
  AlignmentContext,
  StrategyEvaluation,
  StrategyName,
  SharedStrategyName,
  EscalationResult,
} from "./types";

let lastRawStrategyName: SharedStrategyName | null = null;
let lastGatedStrategyName: StrategyName | null = null;
let lastEscalation: EscalationResult = { level: "none" };

export function selectStrategy(context: AlignmentContext): StrategyEvaluation {
  const rawEvaluation = evaluateStrategy(context, lastRawStrategyName);
  let evaluation = gateStrategyByAlignment(rawEvaluation);

  const escalation = computeAlignmentEscalation(evaluation);
  evaluation = { ...evaluation, escalationLevel: escalation.level };

  updateSafeModeFromAlignment(evaluation);

  if (evaluation.alignment < 60) {
    kernelTelemetry.pushAlignmentEvent("floor_breached", {
      strategy: evaluation.name,
      alignment: evaluation.alignment,
    });
  } else if (evaluation.alignment < 70) {
    kernelTelemetry.pushAlignmentEvent("low", {
      strategy: evaluation.name,
      alignment: evaluation.alignment,
    });
  } else {
    kernelTelemetry.pushAlignmentEvent("stable", {
      strategy: evaluation.name,
      alignment: evaluation.alignment,
    });
  }

  if (escalation.level === "critical") {
    evaluation = {
      ...evaluation,
      name: "autonomy_paused_alignment_critical",
      gated: true,
      originalStrategy: rawEvaluation.name,
      notes: `Autonomy paused due to critical alignment level (${evaluation.alignment}%). ${evaluation.notes}`,
    };
  }

  lastRawStrategyName = rawEvaluation.name;
  lastGatedStrategyName = evaluation.name;
  lastEscalation = escalation;

  kernelTelemetry.push(evaluation);

  return evaluation;
}

export function getLastStrategyName(): StrategyName | null {
  return lastGatedStrategyName;
}

export function getLastRawStrategyName(): SharedStrategyName | null {
  return lastRawStrategyName;
}

export function getLastEscalation(): EscalationResult {
  return { ...lastEscalation };
}

export function resetDispatcher(): void {
  lastRawStrategyName = null;
  lastGatedStrategyName = null;
  lastEscalation = { level: "none" };
}
