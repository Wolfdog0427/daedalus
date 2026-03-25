/**
 * Rollback Registry + Outcome Judgment
 *
 * Tracks self-applied changes with bounded evaluation windows.
 * Each tick, active changes are evaluated: if alignment degraded
 * beyond a threshold during the window, the change is rolled back.
 *
 * This gives Daedalus:
 *   - A bounded risk window for self-changes
 *   - Clear "this helped / this hurt" signals
 *   - An automatic escape hatch when a change backfires
 */

import type {
  AppliedChangeRecord,
  ChangeOutcomeResult,
  ChangeOutcomeReason,
  RollbackEvent,
  RollbackRegistrySnapshot,
  RollbackConfig,
  ChangeSurface,
  ChangeImpact,
} from "./types";
import { DEFAULT_ROLLBACK_CONFIG } from "./types";

let activeChanges: AppliedChangeRecord[] = [];
let recentRollbacks: RollbackEvent[] = [];
let acceptedCount = 0;
let rolledBackCount = 0;
let evictedCount = 0;
let currentTickCounter = 0;

let rollbackConfig: RollbackConfig = { ...DEFAULT_ROLLBACK_CONFIG };
let rollbackCallbacks: Map<string, () => void> = new Map();

// ── Registration ────────────────────────────────────────────────────

export function registerChange(
  record: Omit<AppliedChangeRecord, "status" | "appliedAtTick"> & { appliedAtTick?: number },
  rollbackFn?: () => void,
): AppliedChangeRecord {
  const change: AppliedChangeRecord = {
    ...record,
    appliedAtTick: record.appliedAtTick ?? currentTickCounter,
    evaluationWindow: record.evaluationWindow ?? rollbackConfig.defaultEvaluationWindow,
    status: "active",
  };

  if (activeChanges.length >= rollbackConfig.maxActiveChanges) {
    const oldest = activeChanges.shift();
    if (oldest) {
      oldest.status = "evicted";
      evictedCount++;
      rollbackCallbacks.delete(oldest.id);
    }
  }

  activeChanges.push(change);
  if (rollbackFn) {
    rollbackCallbacks.set(change.id, rollbackFn);
  }

  return change;
}

// ── Outcome Evaluation ──────────────────────────────────────────────

export function evaluateChangeOutcome(
  currentAlignment: number,
  change: AppliedChangeRecord,
  degradationThreshold: number = rollbackConfig.degradationThreshold,
): ChangeOutcomeResult {
  const deltaAlignment = currentAlignment - change.baselineAlignment;
  const ticksElapsed = currentTickCounter - change.appliedAtTick;

  if (ticksElapsed < change.evaluationWindow) {
    return { shouldRollback: false, reason: "window_not_reached", deltaAlignment, ticksElapsed };
  }

  if (deltaAlignment < -degradationThreshold) {
    return { shouldRollback: true, reason: "degraded", deltaAlignment, ticksElapsed };
  }

  if (deltaAlignment > 0) {
    return { shouldRollback: false, reason: "improved", deltaAlignment, ticksElapsed };
  }

  return { shouldRollback: false, reason: "neutral", deltaAlignment, ticksElapsed };
}

// ── Per-Tick Processing ─────────────────────────────────────────────

/**
 * Runs rollback evaluation for all active changes. Call once per tick.
 * Returns any rollback events triggered this tick.
 */
export function processRollbacks(currentAlignment: number): RollbackEvent[] {
  currentTickCounter++;
  const events: RollbackEvent[] = [];
  const remaining: AppliedChangeRecord[] = [];

  for (const change of activeChanges) {
    if (change.status !== "active") {
      remaining.push(change);
      continue;
    }

    const result = evaluateChangeOutcome(currentAlignment, change);

    if (result.shouldRollback) {
      change.status = "rolled_back";
      rolledBackCount++;

      const cb = rollbackCallbacks.get(change.id);
      if (cb) {
        cb();
        rollbackCallbacks.delete(change.id);
      }

      const event: RollbackEvent = {
        changeId: change.id,
        reason: result.reason,
        deltaAlignment: result.deltaAlignment,
        rolledBackAt: currentTickCounter,
      };
      events.push(event);
      recentRollbacks.push(event);
    } else if (result.reason === "improved" || result.reason === "neutral") {
      change.status = "accepted";
      acceptedCount++;
      rollbackCallbacks.delete(change.id);
    } else {
      remaining.push(change);
    }
  }

  activeChanges = remaining;

  if (recentRollbacks.length > rollbackConfig.maxRollbackHistory) {
    recentRollbacks = recentRollbacks.slice(
      recentRollbacks.length - rollbackConfig.maxRollbackHistory,
    );
  }

  return events;
}

// ── Snapshot ─────────────────────────────────────────────────────────

export function getRollbackRegistrySnapshot(): RollbackRegistrySnapshot {
  return {
    activeChanges: activeChanges.map(c => ({ ...c })),
    recentRollbacks: [...recentRollbacks],
    acceptedCount,
    rolledBackCount,
    evictedCount,
  };
}

// ── Queries ─────────────────────────────────────────────────────────

export function getActiveChanges(): AppliedChangeRecord[] {
  return activeChanges.filter(c => c.status === "active").map(c => ({ ...c }));
}

export function getRecentRollbacks(): RollbackEvent[] {
  return [...recentRollbacks];
}

export function getCurrentTick(): number {
  return currentTickCounter;
}

// ── Config ──────────────────────────────────────────────────────────

export function getRollbackConfig(): RollbackConfig {
  return { ...rollbackConfig };
}

export function updateRollbackConfig(patch: Partial<RollbackConfig>): RollbackConfig {
  rollbackConfig = { ...rollbackConfig, ...patch };
  return { ...rollbackConfig };
}

// ── Reset ───────────────────────────────────────────────────────────

export function resetRollbackRegistry(): void {
  activeChanges = [];
  recentRollbacks = [];
  acceptedCount = 0;
  rolledBackCount = 0;
  evictedCount = 0;
  currentTickCounter = 0;
  rollbackConfig = { ...DEFAULT_ROLLBACK_CONFIG } as RollbackConfig;
  rollbackCallbacks = new Map();
}
