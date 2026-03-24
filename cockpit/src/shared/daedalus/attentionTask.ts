/**
 * Attention & Task — a unified read-only view of Daedalus's
 * cognitive surface: attention level, focus target, cognitive load,
 * active task presence, and continuity signals.
 *
 * Derived from the expressive field, orchestration state, and
 * operator context. Feeds into the Throne for display but never
 * into governance logic.
 */

export type AttentionTier = "locked" | "focused" | "aware" | "unfocused";

export interface AttentionTaskSnapshot {
  readonly attentionLevel: number;
  readonly attentionTier: AttentionTier;
  readonly focusTarget: string | null;
  readonly cognitiveLoad: number;
  readonly attentionContinuity: number;

  readonly activeTask: string | null;
  readonly taskLoad: number;
  readonly taskContinuity: number;
}

export const ATTENTION_TASK_IDLE: AttentionTaskSnapshot = Object.freeze({
  attentionLevel: 0,
  attentionTier: "unfocused" as AttentionTier,
  focusTarget: null,
  cognitiveLoad: 0,
  attentionContinuity: 1,

  activeTask: null,
  taskLoad: 0,
  taskContinuity: 1,
});
