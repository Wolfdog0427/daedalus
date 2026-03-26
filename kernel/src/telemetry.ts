/**
 * Kernel Alignment Telemetry
 *
 * Records strategy evaluations, alignment events, and maintains
 * history buffers. Provides a snapshot view for the orchestrator
 * API and cockpit UI, including alignment history, drift analysis,
 * escalation state, and safe mode.
 */

import { detectAlignmentDrift } from "./driftDetector";
import { getSafeModeState } from "./safeMode";
import { getRecentApprovalDecisions } from "./autoApproval";
import { getLastRegulationOutput } from "./regulationLoop";
import { getRollbackRegistrySnapshot } from "./rollbackRegistry";
import { getOperatorTrustSnapshot } from "./operatorIdentity";
import { getLastSystemConfidence } from "./alignmentConfidence";
import type {
  StrategyTelemetryEntry,
  KernelTelemetrySnapshot,
  StrategyEvaluation,
  AlignmentHistoryPoint,
  AlignmentEvent,
  AlignmentEventKind,
  EscalationLevel,
  StrategyName,
} from "./types";

const MAX_ENTRIES = 500;
const MAX_STRATEGY_HISTORY = 100;
const MAX_ALIGNMENT_EVENTS = 200;

class KernelTelemetry {
  private entries: StrategyTelemetryEntry[] = [];
  private recentEvaluations: StrategyEvaluation[] = [];
  private alignmentEvents: AlignmentEvent[] = [];

  push(evaluation: StrategyEvaluation): void {
    const now = Date.now();

    const entry: StrategyTelemetryEntry = {
      type: "strategy_evaluated",
      timestamp: now,
      strategy: evaluation.name,
      confidence: evaluation.confidence,
      alignment: evaluation.alignment,
      breakdown: { ...evaluation.alignmentBreakdown },
      gated: evaluation.gated,
      escalationLevel: evaluation.escalationLevel,
    };

    this.entries.push(entry);
    if (this.entries.length > MAX_ENTRIES) {
      this.entries = this.entries.slice(this.entries.length - MAX_ENTRIES);
    }

    this.recentEvaluations.push({ ...evaluation, evaluatedAt: evaluation.evaluatedAt ?? new Date(now).toISOString() });
    if (this.recentEvaluations.length > MAX_STRATEGY_HISTORY) {
      this.recentEvaluations = this.recentEvaluations.slice(
        this.recentEvaluations.length - MAX_STRATEGY_HISTORY,
      );
    }
  }

  pushAlignmentEvent(kind: AlignmentEventKind, payload: Record<string, unknown>): void {
    const event: AlignmentEvent = {
      type: `alignment_${kind}`,
      timestamp: Date.now(),
      ...payload,
    };
    this.alignmentEvents.push(event);
    if (this.alignmentEvents.length > MAX_ALIGNMENT_EVENTS) {
      this.alignmentEvents = this.alignmentEvents.slice(
        this.alignmentEvents.length - MAX_ALIGNMENT_EVENTS,
      );
    }
  }

  getAlignmentHistory(): AlignmentHistoryPoint[] {
    return this.entries.map(e => ({
      timestamp: e.timestamp,
      strategy: e.strategy,
      alignment: e.alignment,
      confidence: e.confidence,
    }));
  }

  getSnapshot(): KernelTelemetrySnapshot {
    const alignmentHistory = this.getAlignmentHistory();
    const drift = detectAlignmentDrift(alignmentHistory);

    const lastEscalation = this.findLastEscalation();

    return {
      events: [...this.entries],
      alignmentEvents: [...this.alignmentEvents],
      recentStrategies: [...this.recentEvaluations],
      alignment: this.recentEvaluations.map(s => ({
        strategy: s.name,
        alignment: s.alignment,
        confidence: s.confidence,
      })),
      alignmentHistory,
      drift,
      lastEscalation,
      safeMode: getSafeModeState(),
      recentApprovals: getRecentApprovalDecisions(),
      lastRegulation: getLastRegulationOutput(),
      rollbackRegistry: getRollbackRegistrySnapshot(),
      operatorTrust: getOperatorTrustSnapshot(),
      systemConfidence: getLastSystemConfidence(),
    };
  }

  private findLastEscalation(): KernelTelemetrySnapshot["lastEscalation"] {
    for (let i = this.entries.length - 1; i >= 0; i--) {
      const e = this.entries[i];
      if (e.escalationLevel && e.escalationLevel !== "none") {
        return {
          level: e.escalationLevel,
          strategy: e.strategy,
          alignment: e.alignment,
        };
      }
    }
    return null;
  }

  getRecentEntries(limit: number): StrategyTelemetryEntry[] {
    return this.entries.slice(-limit);
  }

  getAverageAlignment(window = 5): number {
    const recent = this.entries.slice(-window);
    if (recent.length === 0) return 0;
    return Math.round(recent.reduce((sum, e) => sum + e.alignment, 0) / recent.length);
  }

  clear(): void {
    this.entries = [];
    this.recentEvaluations = [];
    this.alignmentEvents = [];
  }
}

export const kernelTelemetry = new KernelTelemetry();
