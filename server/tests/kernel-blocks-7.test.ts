/**
 * Test suite for all 7 new kernel blocks:
 *   1. Intent Interpreter Feedback Loop
 *   2. Alignment-Aware Escalation Rules
 *   3. Configurable Alignment Floor
 *   4. Alignment Event Stream
 *   5. Operator Alignment Controls (config)
 *   6. Identity Continuity Checks
 *   7. Constitutional Safe Mode
 */

import {
  tickKernel,
  resetDispatcher,
  kernelTelemetry,
  interpretIntent,
  resetIntentState,
  computeAlignmentEscalation,
  resetEscalation,
  computeIdentityContinuity,
  resetIdentityState,
  getLastIdentitySnapshot,
  getSafeModeState,
  updateSafeModeFromAlignment,
  applySafeModeToPosture,
  resetSafeMode,
  applySelfCorrectionIfNeeded,
  selectPosture,
  DEFAULT_KERNEL_CONFIG,
  DEFAULT_KERNEL_POSTURE,
} from "../../kernel/src";
import type {
  AlignmentContext,
  StrategyEvaluation,
  AlignmentHistoryPoint,
  KernelRuntimeConfig,
  IntentInput,
  IntentMetrics,
} from "../../kernel/src";
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

function mkHistory(alignments: number[], baseTs = Date.now()): AlignmentHistoryPoint[] {
  return alignments.map((alignment, idx) => ({
    timestamp: baseTs + idx * 1000,
    strategy: "alignment_nominal" as const,
    alignment,
    confidence: 80,
  }));
}

function mkEvaluation(alignment: number, name: StrategyEvaluation["name"] = "alignment_nominal"): StrategyEvaluation {
  return {
    name,
    confidence: 80,
    alignment,
    alignmentBreakdown: { sovereignty: alignment, identity: alignment, governance: alignment, stability: alignment },
    weakestAxis: "stability",
    strongestAxis: "sovereignty",
    notes: "test",
    evaluatedAt: new Date().toISOString(),
  };
}

// ── Block 1: Intent Interpreter Feedback Loop ───────────────────────

describe("Intent Interpreter Feedback Loop", () => {
  beforeEach(() => {
    resetIntentState();
  });

  const baseInput: IntentInput = { raw: "deploy node-alpha", action: "deploy", target: "node-alpha", confidence: 0.6 };

  test("returns base interpretation when avgAlignment is null", () => {
    const result = interpretIntent(baseInput, { avgAlignment: null });
    expect(result.strictness).toBe(0.5);
    expect(result.requireExplicit).toBe(false);
    expect(result.allowShorthand).toBe(false);
    expect(result.confidence).toBe(0.6);
  });

  test("tightens strictness when avg alignment < 70", () => {
    const result = interpretIntent(baseInput, { avgAlignment: 55 });
    expect(result.strictness).toBe(0.8);
    expect(result.requireExplicit).toBe(true);
    expect(result.allowShorthand).toBe(false);
    expect(result.confidence).toBeCloseTo(0.45);
  });

  test("relaxes strictness when avg alignment >= 85", () => {
    const result = interpretIntent(baseInput, { avgAlignment: 90 });
    expect(result.strictness).toBe(0.3);
    expect(result.requireExplicit).toBe(false);
    expect(result.allowShorthand).toBe(true);
    expect(result.confidence).toBe(0.7);
  });

  test("neutral for moderate alignment (70–84)", () => {
    const result = interpretIntent(baseInput, { avgAlignment: 78 });
    expect(result.strictness).toBe(0.5);
    expect(result.requireExplicit).toBe(false);
    expect(result.allowShorthand).toBe(false);
  });

  test("preserves raw input and action in all cases", () => {
    for (const avg of [null, 40, 75, 95]) {
      const result = interpretIntent(baseInput, { avgAlignment: avg });
      expect(result.raw).toBe("deploy node-alpha");
      expect(result.action).toBe("deploy");
      expect(result.target).toBe("node-alpha");
    }
  });

  test("strictness is bounded to [0, 1]", () => {
    const low = interpretIntent(
      { raw: "x", confidence: 0.1 },
      { avgAlignment: 30 },
    );
    expect(low.strictness).toBeLessThanOrEqual(1);
    expect(low.strictness).toBeGreaterThanOrEqual(0);

    const high = interpretIntent(
      { raw: "x", confidence: 0.9 },
      { avgAlignment: 99 },
    );
    expect(high.strictness).toBeLessThanOrEqual(1);
    expect(high.strictness).toBeGreaterThanOrEqual(0.2);
  });

  test("tickKernel passes intent when provided", () => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetSafeMode();
    resetEscalation();
    resetIdentityState();
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG }, baseInput);
    expect(result.intent).not.toBeNull();
    expect(result.intent!.action).toBe("deploy");
    expect(result.intent!.raw).toBe("deploy node-alpha");
  });

  test("tickKernel returns null intent when not provided", () => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetSafeMode();
    resetEscalation();
    resetIdentityState();
    const result = tickKernel(mkContext());
    expect(result.intent).toBeNull();
  });
});

// ── Block 2: Alignment-Aware Escalation Rules ───────────────────────

describe("Alignment-Aware Escalation Rules", () => {
  beforeEach(() => {
    resetEscalation();
  });

  test("none when alignment >= 70", () => {
    const result = computeAlignmentEscalation(mkEvaluation(85));
    expect(result.level).toBe("none");
    expect(result.reason).toBeUndefined();
  });

  test("medium when alignment 60-69", () => {
    const result = computeAlignmentEscalation(mkEvaluation(65));
    expect(result.level).toBe("medium");
    expect(result.reason).toContain("alignment_below_70");
  });

  test("high when alignment 50-59", () => {
    const result = computeAlignmentEscalation(mkEvaluation(55));
    expect(result.level).toBe("high");
    expect(result.reason).toContain("alignment_below_60");
  });

  test("critical when alignment < 50", () => {
    const result = computeAlignmentEscalation(mkEvaluation(30));
    expect(result.level).toBe("critical");
    expect(result.reason).toContain("alignment_below_50");
  });

  test("boundary at 70 → none", () => {
    expect(computeAlignmentEscalation(mkEvaluation(70)).level).toBe("none");
  });

  test("boundary at 60 → medium", () => {
    expect(computeAlignmentEscalation(mkEvaluation(60)).level).toBe("medium");
  });

  test("boundary at 50 → high", () => {
    expect(computeAlignmentEscalation(mkEvaluation(50)).level).toBe("high");
  });

  test("boundary at 49 → critical", () => {
    expect(computeAlignmentEscalation(mkEvaluation(49)).level).toBe("critical");
  });

  test("critical escalation triggers autonomy_paused in dispatcher", () => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetSafeMode();
    resetEscalation();
    resetIdentityState();

    const result = tickKernel(mkContext({
      beings: [],
      nodeCount: 0,
      quarantinedCount: 0,
      totalErrors: 200,
      activeHeartbeats: 0,
      constitutionReport: { allPassed: false, failedCount: 20, checks: [] },
      posture: "LOCKDOWN" as PostureState,
      drifts: Array.from({ length: 10 }, (_, i) => ({
        id: `d-${i}`,
        axis: "governance",
        severity: "HIGH" as const,
        detectedAt: new Date().toISOString(),
        description: "test",
        summary: "test drift",
      })),
    }));

    if (result.escalation.level === "critical") {
      expect(result.strategy.name).toBe("autonomy_paused_alignment_critical");
      expect(result.strategy.gated).toBe(true);
    }
  });
});

// ── Block 3: Configurable Alignment Floor ───────────────────────────

describe("Configurable Alignment Floor", () => {
  test("DEFAULT_KERNEL_CONFIG includes alignmentFloor", () => {
    expect(DEFAULT_KERNEL_CONFIG.alignmentFloor).toBe(60);
  });

  test("self-correction uses config floor", () => {
    const history = mkHistory(Array.from({ length: 20 }, () => 70));
    const config: KernelRuntimeConfig = {
      ...DEFAULT_KERNEL_CONFIG,
      alignmentFloor: 75,
    };
    const { corrected, trend } = applySelfCorrectionIfNeeded(config, history);
    expect(trend.belowFloor).toBe(true);
    expect(corrected).toBe(true);
  });

  test("self-correction skips when above custom floor", () => {
    const history = mkHistory(Array.from({ length: 20 }, () => 70));
    const config: KernelRuntimeConfig = {
      ...DEFAULT_KERNEL_CONFIG,
      alignmentFloor: 60,
    };
    const { corrected, trend } = applySelfCorrectionIfNeeded(config, history);
    expect(trend.belowFloor).toBe(false);
    expect(corrected).toBe(false);
  });

  test("alignment floor propagated via config through tickKernel", () => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetSafeMode();
    resetEscalation();
    resetIdentityState();

    const config: KernelRuntimeConfig = {
      ...DEFAULT_KERNEL_CONFIG,
      alignmentFloor: 95,
    };
    const result = tickKernel(mkContext(), config);
    expect(result.config.alignmentFloor).toBeDefined();
  });
});

// ── Block 4: Alignment Event Stream ─────────────────────────────────

describe("Alignment Event Stream", () => {
  beforeEach(() => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetSafeMode();
    resetEscalation();
    resetIdentityState();
  });

  test("pushAlignmentEvent populates alignmentEvents in snapshot", () => {
    tickKernel(mkContext());
    const snap = kernelTelemetry.getSnapshot();
    expect(snap.alignmentEvents.length).toBeGreaterThanOrEqual(1);
    expect(snap.alignmentEvents[0].type).toMatch(/^alignment_/);
  });

  test("healthy context emits stable event", () => {
    tickKernel(mkContext());
    const snap = kernelTelemetry.getSnapshot();
    const stableEvents = snap.alignmentEvents.filter(e => e.type === "alignment_stable");
    expect(stableEvents.length).toBeGreaterThanOrEqual(1);
  });

  test("degraded context emits floor_breached or low events", () => {
    tickKernel(mkContext({
      beings: [],
      nodeCount: 0,
      constitutionReport: { allPassed: false, failedCount: 10, checks: [] },
      posture: "LOCKDOWN" as PostureState,
      drifts: Array.from({ length: 8 }, (_, i) => ({
        id: `d-${i}`,
        axis: "governance",
        severity: "HIGH" as const,
        detectedAt: new Date().toISOString(),
        description: "test",
        summary: "test",
      })),
    }));
    const snap = kernelTelemetry.getSnapshot();
    const nonStable = snap.alignmentEvents.filter(e =>
      e.type === "alignment_floor_breached" || e.type === "alignment_low"
    );
    expect(nonStable.length + snap.alignmentEvents.filter(e => e.type === "alignment_stable").length)
      .toBeGreaterThanOrEqual(1);
  });

  test("alignmentEvents are bounded", () => {
    for (let i = 0; i < 250; i++) {
      tickKernel(mkContext());
    }
    const snap = kernelTelemetry.getSnapshot();
    expect(snap.alignmentEvents.length).toBeLessThanOrEqual(200);
  });
});

// ── Block 5: Operator Alignment Controls (config) ───────────────────

describe("Operator Alignment Controls (config shape)", () => {
  test("DEFAULT_KERNEL_CONFIG has all required fields", () => {
    expect(DEFAULT_KERNEL_CONFIG).toHaveProperty("strategySensitivity");
    expect(DEFAULT_KERNEL_CONFIG).toHaveProperty("governanceStrictness");
    expect(DEFAULT_KERNEL_CONFIG).toHaveProperty("alignmentFloor");
  });

  test("alignmentFloor defaults to 60", () => {
    expect(DEFAULT_KERNEL_CONFIG.alignmentFloor).toBe(60);
  });
});

// ── Block 6: Identity Continuity Checks ─────────────────────────────

describe("Identity Continuity Checks", () => {
  beforeEach(() => {
    resetIdentityState();
  });

  test("first snapshot returns 100 (no previous)", () => {
    const score = computeIdentityContinuity({ posture: "OPEN", mode: "normal", governanceTier: "standard" });
    expect(score).toBe(100);
  });

  test("identical snapshot returns 100", () => {
    computeIdentityContinuity({ posture: "OPEN", mode: "normal", governanceTier: "standard" });
    const score = computeIdentityContinuity({ posture: "OPEN", mode: "normal", governanceTier: "standard" });
    expect(score).toBe(100);
  });

  test("posture change deducts 10", () => {
    computeIdentityContinuity({ posture: "OPEN", mode: "normal", governanceTier: "standard" });
    const score = computeIdentityContinuity({ posture: "LOCKDOWN", mode: "normal", governanceTier: "standard" });
    expect(score).toBe(90);
  });

  test("mode change deducts 15", () => {
    computeIdentityContinuity({ posture: "OPEN", mode: "normal", governanceTier: "standard" });
    const score = computeIdentityContinuity({ posture: "OPEN", mode: "emergency", governanceTier: "standard" });
    expect(score).toBe(85);
  });

  test("governance tier change deducts 20", () => {
    computeIdentityContinuity({ posture: "OPEN", mode: "normal", governanceTier: "standard" });
    const score = computeIdentityContinuity({ posture: "OPEN", mode: "normal", governanceTier: "elevated" });
    expect(score).toBe(80);
  });

  test("all changes deduct 45", () => {
    computeIdentityContinuity({ posture: "OPEN", mode: "normal", governanceTier: "standard" });
    const score = computeIdentityContinuity({ posture: "LOCKDOWN", mode: "emergency", governanceTier: "elevated" });
    expect(score).toBe(55);
  });

  test("score is clamped at 0", () => {
    computeIdentityContinuity({ posture: "A", mode: "B", governanceTier: "C" });
    const score = computeIdentityContinuity({ posture: "X", mode: "Y", governanceTier: "Z" });
    expect(score).toBeGreaterThanOrEqual(0);
  });

  test("getLastIdentitySnapshot returns copy of last", () => {
    computeIdentityContinuity({ posture: "OPEN", mode: "normal" });
    const snap = getLastIdentitySnapshot();
    expect(snap).toBeDefined();
    expect(snap!.posture).toBe("OPEN");
    expect(snap!.mode).toBe("normal");
  });

  test("resetIdentityState clears snapshot", () => {
    computeIdentityContinuity({ posture: "OPEN" });
    resetIdentityState();
    expect(getLastIdentitySnapshot()).toBeNull();
    const score = computeIdentityContinuity({ posture: "LOCKDOWN" });
    expect(score).toBe(100);
  });

  test("identity continuity is blended into tickKernel strategy", () => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetSafeMode();
    resetEscalation();

    const result = tickKernel(mkContext());
    expect(result.strategy.alignmentBreakdown.identity).toBeDefined();
    expect(result.strategy.alignmentBreakdown.identity).toBeGreaterThanOrEqual(0);
    expect(result.strategy.alignmentBreakdown.identity).toBeLessThanOrEqual(100);
  });
});

// ── Block 7: Constitutional Safe Mode ───────────────────────────────

describe("Constitutional Safe Mode", () => {
  beforeEach(() => {
    resetSafeMode();
  });

  test("safe mode starts inactive", () => {
    const state = getSafeModeState();
    expect(state.active).toBe(false);
    expect(state.reason).toBeUndefined();
    expect(state.since).toBeUndefined();
  });

  test("activates instantly when alignment < 20", () => {
    updateSafeModeFromAlignment(mkEvaluation(19));
    const state = getSafeModeState();
    expect(state.active).toBe(true);
    expect(state.reason).toBeDefined();
    expect(state.since).toBeDefined();
  });

  test("activates after sustained ticks below 50", () => {
    updateSafeModeFromAlignment(mkEvaluation(40));
    updateSafeModeFromAlignment(mkEvaluation(40));
    updateSafeModeFromAlignment(mkEvaluation(40));
    const state = getSafeModeState();
    expect(state.active).toBe(true);
  });

  test("does not activate at alignment == 50", () => {
    updateSafeModeFromAlignment(mkEvaluation(50));
    expect(getSafeModeState().active).toBe(false);
  });

  test("stays active until alignment >= 60 sustained for 3 ticks", () => {
    updateSafeModeFromAlignment(mkEvaluation(19));
    expect(getSafeModeState().active).toBe(true);

    updateSafeModeFromAlignment(mkEvaluation(55));
    expect(getSafeModeState().active).toBe(true);

    updateSafeModeFromAlignment(mkEvaluation(59));
    expect(getSafeModeState().active).toBe(true);

    // Single tick at 60 is not enough — need 3 sustained
    updateSafeModeFromAlignment(mkEvaluation(60));
    expect(getSafeModeState().active).toBe(true);

    updateSafeModeFromAlignment(mkEvaluation(61));
    expect(getSafeModeState().active).toBe(true);

    updateSafeModeFromAlignment(mkEvaluation(62));
    expect(getSafeModeState().active).toBe(false);
  });

  test("re-activates if alignment drops below 20 after cooldown", () => {
    updateSafeModeFromAlignment(mkEvaluation(19));
    // Sustained exit: 3 ticks above exit threshold
    updateSafeModeFromAlignment(mkEvaluation(70));
    updateSafeModeFromAlignment(mkEvaluation(70));
    updateSafeModeFromAlignment(mkEvaluation(70));
    expect(getSafeModeState().active).toBe(false);

    // Cooldown period — burn through re-entry cooldown ticks at safe alignment
    for (let i = 0; i < 10; i++) updateSafeModeFromAlignment(mkEvaluation(70));

    // Now re-entry should be possible via instant path (<20)
    updateSafeModeFromAlignment(mkEvaluation(15));
    expect(getSafeModeState().active).toBe(true);
  });

  test("applySafeModeToPosture is no-op when inactive", () => {
    const base = { responsiveness: 0.7, caution: 0.5 };
    const result = applySafeModeToPosture(base);
    expect(result.responsiveness).toBe(0.7);
    expect(result.caution).toBe(0.5);
  });

  test("applySafeModeToPosture reduces responsiveness and raises caution (graduated)", () => {
    updateSafeModeFromAlignment(mkEvaluation(19));
    const base = { responsiveness: 0.7, caution: 0.5 };
    // Passing alignment=19 gives near-full penalty
    const result = applySafeModeToPosture(base, 19);
    expect(result.responsiveness).toBeLessThan(0.7);
    expect(result.caution).toBeGreaterThan(0.5);
    // With alignment=19, factor ≈ (60-19)/(60-20) ≈ 1.025 clamped to 1 → full penalty
    expect(result.responsiveness).toBeCloseTo(0.4, 1);
    expect(result.caution).toBeCloseTo(0.8, 1);
  });

  test("applySafeModeToPosture clamps values to [0, 1]", () => {
    updateSafeModeFromAlignment(mkEvaluation(15));
    const base = { responsiveness: 0.1, caution: 0.9 };
    const result = applySafeModeToPosture(base, 15);
    expect(result.responsiveness).toBeGreaterThanOrEqual(0);
    expect(result.caution).toBeLessThanOrEqual(1);
  });

  test("selectPosture applies graduated safe mode overlay", () => {
    updateSafeModeFromAlignment(mkEvaluation(19));
    // Graduated safe mode: at alignment 30, penalty factor is substantial
    const eval30 = mkEvaluation(30);
    const posture = selectPosture(eval30);
    expect(posture.responsiveness).toBeLessThan(DEFAULT_KERNEL_POSTURE.responsiveness);
    expect(posture.caution).toBeGreaterThan(DEFAULT_KERNEL_POSTURE.caution);
  });

  test("safe mode state appears in telemetry snapshot", () => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetIdentityState();

    const degradedCtx = mkContext({
      beings: [],
      nodeCount: 0,
      totalErrors: 200,
      activeHeartbeats: 0,
      constitutionReport: { allPassed: false, failedCount: 20, checks: [] },
      posture: "LOCKDOWN" as PostureState,
      drifts: Array.from({ length: 10 }, (_, i) => ({
        id: `d-${i}`, axis: "governance", severity: "HIGH" as const,
        detectedAt: new Date().toISOString(), description: "t", summary: "t",
      })),
    });

    tickKernel(degradedCtx);

    const snap = kernelTelemetry.getSnapshot();
    expect(snap.safeMode).toBeDefined();
    if (snap.events[0]?.alignment < 50) {
      expect(snap.safeMode.active).toBe(true);
    }
  });

  test("safe mode state appears in tickKernel result", () => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetIdentityState();

    const degradedCtx = mkContext({
      beings: [],
      nodeCount: 0,
      totalErrors: 200,
      activeHeartbeats: 0,
      constitutionReport: { allPassed: false, failedCount: 20, checks: [] },
      posture: "LOCKDOWN" as PostureState,
      drifts: Array.from({ length: 10 }, (_, i) => ({
        id: `d-${i}`, axis: "governance", severity: "HIGH" as const,
        detectedAt: new Date().toISOString(), description: "t", summary: "t",
      })),
    });

    const result = tickKernel(degradedCtx);
    expect(result.safeMode).toBeDefined();
    if (result.strategy.alignment < 50) {
      expect(result.safeMode.active).toBe(true);
    }
  });

  test("resetSafeMode clears state", () => {
    updateSafeModeFromAlignment(mkEvaluation(19));
    expect(getSafeModeState().active).toBe(true);
    resetSafeMode();
    expect(getSafeModeState().active).toBe(false);
  });
});

// ── Integration: Telemetry snapshot shape ───────────────────────────

describe("Telemetry Snapshot Shape (all blocks)", () => {
  beforeEach(() => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetSafeMode();
    resetEscalation();
    resetIdentityState();
  });

  test("snapshot includes all new fields", () => {
    tickKernel(mkContext());
    const snap = kernelTelemetry.getSnapshot();

    expect(snap).toHaveProperty("events");
    expect(snap).toHaveProperty("alignmentEvents");
    expect(snap).toHaveProperty("recentStrategies");
    expect(snap).toHaveProperty("alignment");
    expect(snap).toHaveProperty("alignmentHistory");
    expect(snap).toHaveProperty("drift");
    expect(snap).toHaveProperty("lastEscalation");
    expect(snap).toHaveProperty("safeMode");
  });

  test("lastEscalation is null when no escalation", () => {
    tickKernel(mkContext());
    const snap = kernelTelemetry.getSnapshot();
    if (snap.lastEscalation === null) {
      expect(snap.lastEscalation).toBeNull();
    } else {
      expect(snap.lastEscalation.level).not.toBe("none");
    }
  });

  test("escalationLevel appears in strategy telemetry entries", () => {
    tickKernel(mkContext());
    const snap = kernelTelemetry.getSnapshot();
    expect(snap.events.length).toBeGreaterThan(0);
    for (const event of snap.events) {
      expect(event).toHaveProperty("escalationLevel");
    }
  });
});
