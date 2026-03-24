import type { AttentionTaskSnapshot, AttentionTier } from "./attentionTask";

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, v));
}

export interface AttentionTaskInput {
  /** "unfocused" | "aware" | "focused" | "locked" from ExpressiveField.attention.level */
  expressiveAttentionLevel: string;
  /** 0-1 numeric focus from ExpressiveField.focus */
  expressiveFocus: number;
  /** 0-1 numeric arousal from ExpressiveField.arousal */
  expressiveArousal: number;
  /** 0-1 numeric stability from ExpressiveField.stability */
  expressiveStability: number;
  /** OrchestrationState.intent (idle/guiding/supporting/alert/escalating) */
  orchestrationIntent: string;
  /** Currently active cockpit panel name */
  activePanel: string | null;
  /** Operator intent from the intent model (task/exploration/idle/transition) */
  operatorIntent: string | null;
  /** Number of pending governance proposals */
  pendingProposals: number;
}

const ATTENTION_TIER_MAP: Record<string, AttentionTier> = {
  locked: "locked",
  focused: "focused",
  aware: "aware",
  unfocused: "unfocused",
};

/**
 * Maps the discrete attention level string to our AttentionTier enum.
 */
export function deriveAttentionTier(level: string): AttentionTier {
  return ATTENTION_TIER_MAP[level] ?? "unfocused";
}

/**
 * Computes a 0-1 attention level from the expressive focus and
 * the discrete attention tier.
 */
export function computeAttentionLevel(
  tier: AttentionTier,
  expressiveFocus: number,
): number {
  const tierBase: Record<AttentionTier, number> = {
    locked: 0.9,
    focused: 0.7,
    aware: 0.4,
    unfocused: 0.1,
  };
  return clamp(tierBase[tier] * 0.6 + expressiveFocus * 0.4);
}

/**
 * Cognitive load: a composite of arousal (mental energy demand),
 * pending proposals (governance load), and inverse stability
 * (fragility adds load).
 */
export function computeCognitiveLoad(
  arousal: number,
  pendingProposals: number,
  stability: number,
): number {
  const proposalLoad = clamp(pendingProposals * 0.15);
  const instability = clamp(1 - stability);
  return clamp(arousal * 0.4 + proposalLoad * 0.3 + instability * 0.3);
}

/**
 * Derives the active task name from orchestration intent and
 * operator intent. Returns null when idle.
 */
export function deriveActiveTask(
  orchestrationIntent: string,
  operatorIntent: string | null,
): string | null {
  if (operatorIntent === "task") return "operator-task";
  if (operatorIntent === "exploration") return "exploration";
  if (orchestrationIntent === "guiding") return "guided-task";
  if (orchestrationIntent === "supporting") return "support-task";
  if (orchestrationIntent === "alert" || orchestrationIntent === "escalating") {
    return "alert-response";
  }
  return null;
}

/**
 * Task load: how much cognitive demand the active task imposes.
 * Driven by arousal (energy) and whether a task is actually active.
 */
export function computeTaskLoad(
  arousal: number,
  hasActiveTask: boolean,
): number {
  if (!hasActiveTask) return 0;
  return clamp(0.2 + arousal * 0.6);
}

export function computeAttentionTask(
  input: AttentionTaskInput,
): AttentionTaskSnapshot {
  const tier = deriveAttentionTier(input.expressiveAttentionLevel);
  const attentionLevel = computeAttentionLevel(tier, input.expressiveFocus);
  const cognitiveLoad = computeCognitiveLoad(
    input.expressiveArousal,
    input.pendingProposals,
    input.expressiveStability,
  );
  const activeTask = deriveActiveTask(
    input.orchestrationIntent,
    input.operatorIntent,
  );
  const taskLoad = computeTaskLoad(input.expressiveArousal, activeTask !== null);

  return Object.freeze({
    attentionLevel,
    attentionTier: tier,
    focusTarget: input.activePanel,
    cognitiveLoad,
    attentionContinuity: input.expressiveStability,
    activeTask,
    taskLoad,
    taskContinuity: input.expressiveStability,
  });
}
