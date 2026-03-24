import {
  selectStrategy,
  resetDispatcher,
  getLastStrategyName,
  kernelTelemetry,
  computeAlignmentBreakdown,
  explainStrategy,
  resetSafeMode,
  resetIdentityState,
} from "../../kernel/src";
import type { AlignmentContext } from "../../shared/daedalus/strategyAlignment";
import type { BeingPresenceDetail, PostureState } from "../../shared/daedalus/contracts";

function mkBeing(overrides: Partial<BeingPresenceDetail> = {}): BeingPresenceDetail {
  return {
    id: overrides.id ?? "operator",
    label: "Operator",
    role: "operator",
    presenceMode: "active",
    isGuiding: true,
    influenceLevel: 0.9,
    continuity: { healthy: true, streak: 10, lastCheckedAt: new Date().toISOString() },
    ...overrides,
  } as BeingPresenceDetail;
}

function mkContext(overrides: Partial<AlignmentContext> = {}): AlignmentContext {
  return {
    beings: [mkBeing()],
    constitutionReport: { allPassed: true, failedCount: 0, checks: [] },
    posture: "OPEN" as PostureState,
    postureReason: "default",
    overrides: [],
    drifts: [],
    votes: [],
    nodeCount: 3,
    quarantinedCount: 0,
    totalErrors: 0,
    activeHeartbeats: 3,
    ...overrides,
  };
}

describe("Kernel Strategy Dispatcher", () => {
  beforeEach(() => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetSafeMode();
    resetIdentityState();
  });

  describe("selectStrategy", () => {
    test("returns a valid StrategyEvaluation", () => {
      const result = selectStrategy(mkContext());
      expect(result).toHaveProperty("name");
      expect(result).toHaveProperty("confidence");
      expect(result).toHaveProperty("alignment");
      expect(result).toHaveProperty("alignmentBreakdown");
      expect(result).toHaveProperty("weakestAxis");
      expect(result).toHaveProperty("strongestAxis");
      expect(result).toHaveProperty("notes");
      expect(result).toHaveProperty("evaluatedAt");
    });

    test("records the strategy name for subsequent calls", () => {
      expect(getLastStrategyName()).toBeNull();
      selectStrategy(mkContext());
      expect(getLastStrategyName()).not.toBeNull();
    });

    test("pushes a telemetry entry on each evaluation", () => {
      const snap1 = kernelTelemetry.getSnapshot();
      expect(snap1.events).toHaveLength(0);

      selectStrategy(mkContext());
      const snap2 = kernelTelemetry.getSnapshot();
      expect(snap2.events).toHaveLength(1);
      expect(snap2.events[0].type).toBe("strategy_evaluated");

      selectStrategy(mkContext());
      const snap3 = kernelTelemetry.getSnapshot();
      expect(snap3.events).toHaveLength(2);
    });

    test("telemetry snapshot includes alignment feed", () => {
      selectStrategy(mkContext());
      selectStrategy(mkContext());
      const snap = kernelTelemetry.getSnapshot();
      expect(snap.alignment).toHaveLength(2);
      expect(snap.alignment[0]).toHaveProperty("strategy");
      expect(snap.alignment[0]).toHaveProperty("alignment");
      expect(snap.alignment[0]).toHaveProperty("confidence");
    });

    test("telemetry recentStrategies contains full evaluations", () => {
      selectStrategy(mkContext());
      const snap = kernelTelemetry.getSnapshot();
      expect(snap.recentStrategies).toHaveLength(1);
      expect(snap.recentStrategies[0]).toHaveProperty("alignmentBreakdown");
      expect(snap.recentStrategies[0]).toHaveProperty("notes");
    });
  });

  describe("computeAlignmentBreakdown (kernel)", () => {
    test("null strategy name returns unbiased baseline", () => {
      const ctx = mkContext();
      const breakdown = computeAlignmentBreakdown(null, ctx);
      expect(breakdown.sovereignty).toBeGreaterThanOrEqual(0);
      expect(breakdown.sovereignty).toBeLessThanOrEqual(100);
      expect(breakdown.identity).toBeGreaterThanOrEqual(0);
      expect(breakdown.governance).toBeGreaterThanOrEqual(0);
      expect(breakdown.stability).toBeGreaterThanOrEqual(0);
    });

    test("strategy-specific bias shifts scores", () => {
      const ctx = mkContext();
      const neutral = computeAlignmentBreakdown(null, ctx);
      const biased = computeAlignmentBreakdown("sovereignty_stable", ctx);
      expect(biased.sovereignty).toBeGreaterThanOrEqual(neutral.sovereignty);
    });

    test("alignment_degraded applies negative bias to all axes", () => {
      const ctx = mkContext();
      const neutral = computeAlignmentBreakdown(null, ctx);
      const degraded = computeAlignmentBreakdown("alignment_degraded", ctx);
      expect(degraded.sovereignty).toBeLessThanOrEqual(neutral.sovereignty);
      expect(degraded.identity).toBeLessThanOrEqual(neutral.identity);
      expect(degraded.governance).toBeLessThanOrEqual(neutral.governance);
      expect(degraded.stability).toBeLessThanOrEqual(neutral.stability);
    });

    test("scores are always clamped 0-100", () => {
      const ctx = mkContext({
        nodeCount: 0,
        quarantinedCount: 0,
        totalErrors: 100,
        activeHeartbeats: 0,
        beings: [],
        constitutionReport: { allPassed: false, failedCount: 10, checks: [] },
        posture: "LOCKDOWN" as PostureState,
        drifts: Array.from({ length: 10 }, (_, i) => ({
          id: `d-${i}`,
          axis: "governance",
          severity: "HIGH" as const,
          detectedAt: new Date().toISOString(),
          description: "test drift",
          summary: "test drift summary",
        })),
      });
      for (const strat of [null, "alignment_degraded", "stability_recovery"] as const) {
        const b = computeAlignmentBreakdown(strat, ctx);
        for (const axis of ["sovereignty", "identity", "governance", "stability"] as const) {
          expect(b[axis]).toBeGreaterThanOrEqual(0);
          expect(b[axis]).toBeLessThanOrEqual(100);
        }
      }
    });
  });

  describe("explainStrategy", () => {
    test("includes axis spread warning for wide spread", () => {
      const breakdown = { sovereignty: 90, identity: 90, governance: 30, stability: 90 };
      const ctx = mkContext();
      const notes = explainStrategy("governance_undercorrection", breakdown, ctx);
      expect(notes).toContain("spread");
    });

    test("includes quarantine count in stability_recovery notes", () => {
      const breakdown = { sovereignty: 80, identity: 80, governance: 80, stability: 20 };
      const ctx = mkContext({ quarantinedCount: 3 });
      const notes = explainStrategy("stability_recovery", breakdown, ctx);
      expect(notes).toContain("3");
      expect(notes).toContain("quarantined");
    });

    test("includes constitution failures in identity_reinforcement notes", () => {
      const breakdown = { sovereignty: 80, identity: 20, governance: 80, stability: 80 };
      const ctx = mkContext({
        constitutionReport: { allPassed: false, failedCount: 5, checks: [] },
      });
      const notes = explainStrategy("identity_reinforcement", breakdown, ctx);
      expect(notes).toContain("5");
      expect(notes).toContain("failure");
    });
  });

  describe("telemetry edge cases", () => {
    test("getAverageAlignment returns 0 when empty", () => {
      expect(kernelTelemetry.getAverageAlignment()).toBe(0);
    });

    test("getAverageAlignment computes over window", () => {
      selectStrategy(mkContext());
      selectStrategy(mkContext());
      selectStrategy(mkContext());
      const avg = kernelTelemetry.getAverageAlignment(3);
      expect(avg).toBeGreaterThan(0);
      expect(avg).toBeLessThanOrEqual(100);
    });

    test("getAlignmentHistory returns all entries", () => {
      for (let i = 0; i < 5; i++) selectStrategy(mkContext());
      const history = kernelTelemetry.getAlignmentHistory();
      expect(history).toHaveLength(5);
      expect(history[0]).toHaveProperty("timestamp");
      expect(history[0]).toHaveProperty("alignment");
      expect(history[0]).toHaveProperty("strategy");
    });

    test("clear wipes all telemetry", () => {
      selectStrategy(mkContext());
      kernelTelemetry.clear();
      const snap = kernelTelemetry.getSnapshot();
      expect(snap.events).toHaveLength(0);
      expect(snap.recentStrategies).toHaveLength(0);
      expect(snap.alignment).toHaveLength(0);
    });
  });
});
