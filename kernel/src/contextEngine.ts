/**
 * Context-Aware Expressive Modulation
 *
 * Computes sub-posture and overlay boosts based on the current task type
 * and environment. These are suggestions that feed into the expressive
 * aggregation layer — they NEVER override constitutional posture bands.
 */

import type { ContextState, ContextualModulation } from "./types";
import { SubPosture, ExpressiveOverlay } from "./types";

let currentContext: ContextState = { taskType: "idle", environment: "normal" };

export function setContext(ctx: Partial<ContextState>): ContextState {
  currentContext = { ...currentContext, ...ctx };
  return { ...currentContext };
}

export function getContext(): ContextState {
  return { ...currentContext };
}

export function computeContextualModulation(
  context: ContextState = currentContext,
): ContextualModulation {
  let subPostureBoost = SubPosture.NONE;
  let overlayBoost = ExpressiveOverlay.NONE;
  let reason = "idle";

  switch (context.taskType) {
    case "analysis":
      subPostureBoost = SubPosture.ANALYTIC;
      reason = "analysis task active";
      break;
    case "creative":
      subPostureBoost = SubPosture.CREATIVE;
      reason = "creative task active";
      break;
    case "sensitive":
      subPostureBoost = SubPosture.SENSITIVE;
      reason = "sensitive task active";
      break;
    case "review":
      subPostureBoost = SubPosture.ANALYTIC;
      reason = "review task active";
      break;
    case "idle":
      reason = "idle";
      break;
  }

  switch (context.environment) {
    case "crisis":
      overlayBoost = ExpressiveOverlay.ALERT;
      reason += " + crisis environment";
      break;
    case "handoff":
      subPostureBoost = SubPosture.SUPPORTIVE;
      overlayBoost = ExpressiveOverlay.CALM;
      reason += " + handoff environment";
      break;
    case "recovery":
      overlayBoost = ExpressiveOverlay.RECOVERY;
      reason += " + recovery environment";
      break;
    case "normal":
      break;
  }

  return { subPostureBoost, overlayBoost, reason };
}

export function resetContextEngine(): void {
  currentContext = { taskType: "idle", environment: "normal" };
}
