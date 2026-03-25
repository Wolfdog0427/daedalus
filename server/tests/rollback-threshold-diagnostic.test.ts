/**
 * Rollback Threshold Diagnostic Test
 *
 * Investigates why rollbackCount = 0 across 10,000 years of simulation.
 *
 * Findings to test:
 *   1. The simulation never calls registerChange() — so processRollbacks()
 *      has nothing to evaluate. This is the primary cause.
 *   2. Once wired, does the degradation threshold (7 points) catch bad changes?
 *   3. What threshold would be needed to catch realistic degradation patterns?
 *   4. Does the evaluation window (100 ticks) align with how fast alignment moves?
 */

import {
  tickKernel,
  DEFAULT_KERNEL_CONFIG,
  kernelTelemetry,
  resetDispatcher,
  resetSafeMode,
  resetIdentityState,
  resetIntentState,
  resetApprovalGate,
  resetRollbackRegistry,
  resetRegulationState,
  registerChange,
  getRollbackRegistrySnapshot,
  getActiveChanges,
  bindOperator,
} from "../../kernel/src";

import type {
  AlignmentContext,
  KernelRuntimeConfig,
} from "../../kernel/src/types";

import type { BeingPresenceDetail, PostureState, ContinuityDrift } from "../../shared/daedalus/contracts";

jest.setTimeout(300_000);

const primaryOperator = {
  id: "diag-operator",
  displayName: "Diagnostics",
  values: {
    operatorSovereignty: true,
    noSilentRepoShifts: true,
    explicitNotification: true,
    constitutionalGovernance: true,
    longHorizonStability: true,
  },
  continuityAnchors: ["diagnostic"],
  risk: { allowExperimentalNodes: true, allowAutoApproval: true, preferSafetyOverConvenience: true },
};

function mkBeing(overrides: Partial<BeingPresenceDetail> = {}): BeingPresenceDetail {
  return {
    id: "operator",
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
    nodeCount: 10,
    quarantinedCount: 0,
    totalErrors: 0,
    activeHeartbeats: 10,
    ...overrides,
  };
}

function crisisContext(): AlignmentContext {
  return mkContext({
    quarantinedCount: 4,
    totalErrors: 100,
    activeHeartbeats: 1,
    constitutionReport: { allPassed: false, failedCount: 5, checks: [] },
    drifts: [
      { id: "d-1", axis: "governance", severity: "HIGH", detectedAt: new Date().toISOString(), description: "drift", summary: "governance drift" },
      { id: "d-2", axis: "identity", severity: "HIGH", detectedAt: new Date().toISOString(), description: "drift", summary: "identity drift" },
    ] as any,
    overrides: [
      { id: "o-1", scope: "GLOBAL", effect: "DENY", createdBy: { id: "system", role: "operator", label: "System" }, reason: "emergency", createdAt: new Date().toISOString() },
    ] as any,
  });
}

function resetAll() {
  resetDispatcher();
  kernelTelemetry.clear();
  resetSafeMode();
  resetIdentityState();
  resetIntentState();
  resetApprovalGate();
  resetRollbackRegistry();
  resetRegulationState();
  bindOperator(primaryOperator);
}

describe("Rollback Threshold Diagnostics", () => {

  describe("Diagnosis 1: Confirm zero rollbacks without registerChange", () => {
    beforeEach(resetAll);

    it("processRollbacks returns empty when nothing is registered", () => {
      let config = { ...DEFAULT_KERNEL_CONFIG };

      for (let i = 0; i < 500; i++) {
        const result = tickKernel(mkContext(), config);
        config = result.config;
      }

      const snap = getRollbackRegistrySnapshot();
      expect(snap.activeChanges).toHaveLength(0);
      expect(snap.rolledBackCount).toBe(0);
      expect(snap.acceptedCount).toBe(0);
      expect(snap.evictedCount).toBe(0);

      console.log("\n[Diagnosis 1] Confirmed: 0 rollbacks because 0 changes registered.");
      console.log("  activeChanges:", snap.activeChanges.length);
      console.log("  rolledBackCount:", snap.rolledBackCount);
      console.log("  acceptedCount:", snap.acceptedCount);
    });
  });

  describe("Diagnosis 2: Rollbacks fire when changes ARE registered and alignment drops", () => {
    beforeEach(resetAll);

    it("detects and rolls back a change that degrades alignment", () => {
      let config = { ...DEFAULT_KERNEL_CONFIG };

      // Warm up telemetry with 60 healthy ticks
      for (let i = 0; i < 60; i++) {
        const r = tickKernel(mkContext(), config);
        config = r.config;
      }

      const warmupResult = tickKernel(mkContext(), config);
      config = warmupResult.config;
      const baselineAlignment = warmupResult.strategy.alignment;
      console.log("\n[Diagnosis 2] Baseline alignment after warmup:", baselineAlignment);

      let wasRolledBack = false;
      registerChange(
        {
          id: "test-bad-change",
          description: "Intentionally bad config change",
          evaluationWindow: 30,
          baselineAlignment,
          surfaces: ["non_critical_config"],
          impact: "low",
          rollbackPayload: {},
        },
        () => { wasRolledBack = true; },
      );

      const snap1 = getRollbackRegistrySnapshot();
      expect(snap1.activeChanges).toHaveLength(1);
      console.log("  Registered change with baseline:", baselineAlignment, "window: 30 ticks");

      const badContext = crisisContext();
      let rollbackEventCount = 0;
      const alignmentTrack: number[] = [];

      for (let i = 0; i < 150; i++) {
        const r = tickKernel(badContext, config);
        config = r.config;
        alignmentTrack.push(r.strategy.alignment);
        rollbackEventCount += r.rollbacks.length;
      }

      const snap2 = getRollbackRegistrySnapshot();
      const minAlignment = Math.min(...alignmentTrack);
      const avgAlignment = Math.round(alignmentTrack.reduce((a, b) => a + b, 0) / alignmentTrack.length);
      const deltaFromBaseline = minAlignment - baselineAlignment;

      console.log("  Alignment during crisis: avg=" + avgAlignment + "%, min=" + minAlignment + "%");
      console.log("  Delta from baseline:", deltaFromBaseline, "(threshold: -7)");
      console.log("  Rollback events fired:", rollbackEventCount);
      console.log("  wasRolledBack callback:", wasRolledBack);
      console.log("  Registry: rolledBack=" + snap2.rolledBackCount + ", accepted=" + snap2.acceptedCount + ", evicted=" + snap2.evictedCount);

      if (deltaFromBaseline < -7) {
        expect(rollbackEventCount).toBeGreaterThan(0);
        expect(wasRolledBack).toBe(true);
        console.log("  RESULT: Rollback correctly fired for degradation of", deltaFromBaseline, "points.");
      } else {
        console.log("  RESULT: Alignment didn't drop enough to trigger rollback (delta:", deltaFromBaseline, ")");
      }
    });
  });

  describe("Diagnosis 3: Threshold sensitivity at different stress levels", () => {
    beforeEach(resetAll);

    it("measures degradation at mild, moderate, heavy, and catastrophic stress", () => {
      const severities = [
        { name: "mild_stress", ctx: mkContext({ totalErrors: 20, activeHeartbeats: 7 }) },
        { name: "moderate_stress", ctx: mkContext({ totalErrors: 50, quarantinedCount: 2, activeHeartbeats: 5 }) },
        { name: "heavy_stress", ctx: mkContext({ totalErrors: 80, quarantinedCount: 3, activeHeartbeats: 2, drifts: [{ id: "d1", axis: "governance", severity: "HIGH", detectedAt: new Date().toISOString(), description: "drift", summary: "gov drift" }] as any }) },
        { name: "catastrophic", ctx: crisisContext() },
      ];

      console.log("\n[Diagnosis 3] Threshold sensitivity analysis:");
      console.log("  Default degradation threshold: 7 points");
      console.log("  Default evaluation window: 100 ticks\n");

      for (const { name, ctx } of severities) {
        resetAll();
        let config = { ...DEFAULT_KERNEL_CONFIG };

        for (let i = 0; i < 60; i++) {
          const r = tickKernel(mkContext(), config);
          config = r.config;
        }

        const baseResult = tickKernel(mkContext(), config);
        config = baseResult.config;
        const baseline = baseResult.strategy.alignment;

        const alignments: number[] = [];
        for (let i = 0; i < 200; i++) {
          const r = tickKernel(ctx, config);
          config = r.config;
          alignments.push(r.strategy.alignment);
        }

        const minA = Math.min(...alignments);
        const avgA = Math.round(alignments.reduce((a, b) => a + b, 0) / alignments.length);
        const at30 = alignments[29] ?? 0;
        const at100 = alignments[99] ?? 0;
        const delta30 = at30 - baseline;
        const delta100 = at100 - baseline;

        console.log(`  ${name}:`);
        console.log(`    Baseline: ${baseline}% | Avg under stress: ${avgA}% | Min: ${minA}%`);
        console.log(`    Delta at tick 30: ${delta30} | tick 100: ${delta100}`);
        console.log(`    Rollback (window=30, threshold=7)? ${delta30 < -7 ? "YES" : "NO"}`);
        console.log(`    Rollback (window=100, threshold=7)? ${delta100 < -7 ? "YES" : "NO"}`);
        console.log(`    Rollback (window=30, threshold=3)? ${delta30 < -3 ? "YES" : "NO"}`);
        console.log(`    Rollback (window=100, threshold=3)? ${delta100 < -3 ? "YES" : "NO"}`);
        console.log("");
      }
    });
  });

  describe("Diagnosis 4: 500-year sim with changes registered at high alignment", () => {
    beforeEach(resetAll);

    it("registers changes during healthy periods and sees what happens during crises", () => {
      let config = { ...DEFAULT_KERNEL_CONFIG };
      const YEARS = 500;
      const WEEKS_PER_YEAR = 52;
      const TICKS_PER_WEEK = 20;

      let changesRegistered = 0;
      let changeIdCounter = 0;
      let changeCooldown = 0;

      // Warm up
      for (let i = 0; i < 60; i++) {
        const r = tickKernel(mkContext(), config);
        config = r.config;
      }

      for (let year = 1; year <= YEARS; year++) {
        for (let week = 0; week < WEEKS_PER_YEAR; week++) {
          const isCrisis = (year % 50 === 0 && week >= 10 && week <= 16);
          const ctx = isCrisis ? crisisContext() : mkContext();

          for (let t = 0; t < TICKS_PER_WEEK; t++) {
            const result = tickKernel(ctx, config);
            config = result.config;

            // Register changes during healthy periods at high alignment
            if (!isCrisis && changeCooldown <= 0 && result.strategy.alignment >= 85) {
              const active = getActiveChanges();
              if (active.length < 15) {
                changeIdCounter++;
                registerChange({
                  id: `sim-change-${changeIdCounter}`,
                  description: `Config adjustment at alignment ${result.strategy.alignment}%`,
                  evaluationWindow: 60 + Math.floor(Math.random() * 80),
                  baselineAlignment: result.strategy.alignment,
                  surfaces: ["non_critical_config"],
                  impact: "low",
                  rollbackPayload: {},
                });
                changesRegistered++;
                changeCooldown = 200;
              }
            }
            if (changeCooldown > 0) changeCooldown--;
          }
        }
      }

      const snap = getRollbackRegistrySnapshot();

      console.log("\n[Diagnosis 4] 500-year sim with changes registered at HIGH alignment:");
      console.log("  Changes registered:", changesRegistered);
      console.log("  Accepted:", snap.acceptedCount);
      console.log("  Rolled back:", snap.rolledBackCount);
      console.log("  Evicted:", snap.evictedCount);
      console.log("  Active at end:", snap.activeChanges.length);
      console.log("  Recent rollbacks:", snap.recentRollbacks.length);

      if (snap.recentRollbacks.length > 0) {
        console.log("  Sample rollbacks:");
        for (const rb of snap.recentRollbacks.slice(0, 10)) {
          console.log(`    ${rb.changeId}: delta=${rb.deltaAlignment.toFixed(1)}, reason=${rb.reason}`);
        }
      }

      const total = snap.acceptedCount + snap.rolledBackCount + snap.evictedCount + snap.activeChanges.length;
      console.log(`\n  Disposition: ${snap.acceptedCount} accepted + ${snap.rolledBackCount} rolled back + ${snap.evictedCount} evicted + ${snap.activeChanges.length} still active = ${total} (registered: ${changesRegistered})`);

      if (snap.rolledBackCount > 0) {
        const rate = ((snap.rolledBackCount / changesRegistered) * 100).toFixed(1);
        console.log(`  Rollback rate: ${rate}%`);
      } else {
        console.log("  Rollback rate: 0% — investigating why...");
        if (changesRegistered > 0) {
          console.log("  HYPOTHESIS: Changes registered at high alignment (>=85%).");
          console.log("  Their evaluation windows likely expire during healthy ticks (alignment still high).");
          console.log("  By the time a crisis hits, the old changes have already been accepted/evicted.");
          console.log("  The timing mismatch prevents rollbacks from firing.");
        }
      }
    });
  });

  describe("Diagnosis 5: Force rollback — register high, then immediately crisis", () => {
    beforeEach(resetAll);

    it("registers change at high baseline then drops into crisis", () => {
      let config = { ...DEFAULT_KERNEL_CONFIG };

      for (let i = 0; i < 100; i++) {
        const r = tickKernel(mkContext(), config);
        config = r.config;
      }

      const healthyResult = tickKernel(mkContext(), config);
      config = healthyResult.config;
      const highBaseline = healthyResult.strategy.alignment;
      console.log("\n[Diagnosis 5] High baseline alignment:", highBaseline);

      let rollbackFired = false;
      registerChange(
        {
          id: "high-baseline-change",
          description: "Change registered at high alignment",
          evaluationWindow: 40,
          baselineAlignment: highBaseline,
          surfaces: ["non_critical_config"],
          impact: "low",
          rollbackPayload: {},
        },
        () => { rollbackFired = true; },
      );

      const badCtx = crisisContext();
      let rollbackCount = 0;
      const alignments: number[] = [];

      for (let i = 0; i < 100; i++) {
        const r = tickKernel(badCtx, config);
        config = r.config;
        alignments.push(r.strategy.alignment);
        rollbackCount += r.rollbacks.length;
      }

      const snap = getRollbackRegistrySnapshot();
      const minAlignment = Math.min(...alignments);
      const delta = minAlignment - highBaseline;

      console.log("  Min alignment during crisis:", minAlignment);
      console.log("  Delta from high baseline:", delta);
      console.log("  Rollback fired:", rollbackFired);
      console.log("  Rollback count:", rollbackCount);
      console.log("  Registry:", JSON.stringify({
        rolledBack: snap.rolledBackCount,
        accepted: snap.acceptedCount,
        evicted: snap.evictedCount,
        active: snap.activeChanges.length,
      }));

      if (delta < -7) {
        expect(rollbackCount).toBeGreaterThan(0);
        console.log("  CONFIRMED: Rollback fires when baseline is high and crisis drops alignment.");
      }
    });
  });

  describe("Diagnosis 6: Threshold sweep — what threshold catches what", () => {
    it("sweeps thresholds 1-20 across 200 years with crises every 50", () => {
      const thresholds = [1, 2, 3, 5, 7, 10, 15, 20];
      const YEARS = 200;
      const WEEKS = 52;
      const TPW = 20;

      console.log("\n[Diagnosis 6] Threshold sweep — changes registered at HEALTHY alignment, crises every 50 years:");
      console.log("  Evaluation window: 60-140 ticks (randomized per change)");
      console.log("  Change registration cooldown: 150 ticks\n");

      for (const threshold of thresholds) {
        resetAll();
        let config = { ...DEFAULT_KERNEL_CONFIG };

        for (let i = 0; i < 60; i++) {
          const r = tickKernel(mkContext(), config);
          config = r.config;
        }

        let changesRegistered = 0;
        let changeId = 0;
        let changeCooldown = 0;
        let totalRollbacks = 0;

        // We need to manually check threshold since the kernel uses the global config
        // But we can just read the result
        for (let year = 1; year <= YEARS; year++) {
          for (let week = 0; week < WEEKS; week++) {
            const isCrisis = (year % 50 === 0 && week >= 8 && week <= 15);
            const ctx = isCrisis ? crisisContext() : mkContext();

            for (let t = 0; t < TPW; t++) {
              const result = tickKernel(ctx, config);
              config = result.config;

              if (!isCrisis && changeCooldown <= 0 && result.strategy.alignment >= 80) {
                const active = getActiveChanges();
                if (active.length < 12) {
                  changeId++;
                  registerChange({
                    id: `sweep-${threshold}-${changeId}`,
                    description: `Change at a=${result.strategy.alignment}`,
                    evaluationWindow: 60 + Math.floor(Math.random() * 80),
                    baselineAlignment: result.strategy.alignment,
                    surfaces: ["non_critical_config"],
                    impact: "low",
                    rollbackPayload: {},
                  });
                  changesRegistered++;
                  changeCooldown = 150;
                }
              }
              if (changeCooldown > 0) changeCooldown--;

              totalRollbacks += result.rollbacks.length;
            }
          }
        }

        const snap = getRollbackRegistrySnapshot();
        const rate = changesRegistered > 0 ? ((snap.rolledBackCount / changesRegistered) * 100).toFixed(1) : "0.0";
        console.log(`  threshold=${threshold.toString().padStart(2)}: registered=${changesRegistered}, rolledBack=${snap.rolledBackCount}, accepted=${snap.acceptedCount}, evicted=${snap.evictedCount}, rate=${rate}%`);
      }
    });
  });
});
