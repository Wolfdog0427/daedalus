import {
  tickKernel,
  selectStrategy,
  resetDispatcher,
  kernelTelemetry,
  gateStrategyByAlignment,
  applySelfCorrectionIfNeeded,
  computeRecentAlignmentTrend,
  selectPosture,
  detectAlignmentDrift,
  resetSafeMode,
  resetIdentityState,
  resetIntentState,
  DEFAULT_KERNEL_CONFIG,
  DEFAULT_KERNEL_POSTURE,
} from "../../kernel/src";
import type {
  AlignmentContext,
  StrategyEvaluation,
  AlignmentHistoryPoint,
  KernelRuntimeConfig,
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

describe("Alignment Drift Detector", () => {
  test("no drift with empty history", () => {
    const result = detectAlignmentDrift([]);
    expect(result.drifting).toBe(false);
    expect(result.delta).toBe(0);
    expect(result.firstAlignment).toBeNull();
    expect(result.lastAlignment).toBeNull();
  });

  test("no drift with single entry", () => {
    const result = detectAlignmentDrift(mkHistory([85]));
    expect(result.drifting).toBe(false);
  });

  test("no drift when alignment is stable", () => {
    const result = detectAlignmentDrift(mkHistory([85, 84, 85, 86, 85]));
    expect(result.drifting).toBe(false);
    expect(result.delta).toBeGreaterThanOrEqual(-10);
  });

  test("detects drift when alignment drops by threshold", () => {
    const result = detectAlignmentDrift(mkHistory([90, 88, 85, 80, 75, 70]));
    expect(result.drifting).toBe(true);
    expect(result.delta).toBe(-20);
    expect(result.firstAlignment).toBe(90);
    expect(result.lastAlignment).toBe(70);
  });

  test("no drift when alignment increases", () => {
    const result = detectAlignmentDrift(mkHistory([60, 65, 70, 75, 80]));
    expect(result.drifting).toBe(false);
    expect(result.delta).toBe(20);
  });

  test("drift window is bounded", () => {
    const long = mkHistory(Array.from({ length: 50 }, (_, i) => 90 - i));
    const result = detectAlignmentDrift(long);
    expect(result.window).toBe(40);
  });
});

describe("Self-Correction Loop", () => {
  test("returns null avgAlignment with no history", () => {
    const trend = computeRecentAlignmentTrend([]);
    expect(trend.avgAlignment).toBeNull();
    expect(trend.belowFloor).toBe(false);
    expect(trend.sampleCount).toBe(0);
  });

  test("healthy alignment does not trigger correction", () => {
    const history = mkHistory([85, 88, 90, 87, 86]);
    const { config, corrected } = applySelfCorrectionIfNeeded(
      { ...DEFAULT_KERNEL_CONFIG },
      history,
    );
    expect(corrected).toBe(false);
    expect(config.strategySensitivity).toBe(DEFAULT_KERNEL_CONFIG.strategySensitivity);
    expect(config.governanceStrictness).toBe(DEFAULT_KERNEL_CONFIG.governanceStrictness);
  });

  test("low alignment triggers correction", () => {
    const history = mkHistory([60, 55, 50, 65, 60, 58, 62, 55]);
    const { config, corrected, trend } = applySelfCorrectionIfNeeded(
      { ...DEFAULT_KERNEL_CONFIG },
      history,
    );
    expect(corrected).toBe(true);
    expect(trend.belowFloor).toBe(true);
    expect(config.strategySensitivity).toBeLessThan(DEFAULT_KERNEL_CONFIG.strategySensitivity);
    expect(config.governanceStrictness).toBeGreaterThan(DEFAULT_KERNEL_CONFIG.governanceStrictness);
  });

  test("correction is bounded: sensitivity ≥ 0", () => {
    const history = mkHistory(Array.from({ length: 20 }, () => 40));
    const { config } = applySelfCorrectionIfNeeded(
      { strategySensitivity: 0.05, governanceStrictness: 0.95, alignmentFloor: 60 },
      history,
    );
    expect(config.strategySensitivity).toBeGreaterThanOrEqual(0);
    expect(config.governanceStrictness).toBeLessThanOrEqual(1);
  });

  test("correction accumulates over repeated calls", () => {
    const history = mkHistory(Array.from({ length: 20 }, () => 50));
    let cfg: KernelRuntimeConfig = { ...DEFAULT_KERNEL_CONFIG };
    for (let i = 0; i < 5; i++) {
      const result = applySelfCorrectionIfNeeded(cfg, history);
      cfg = result.config;
    }
    expect(cfg.strategySensitivity).toBeLessThan(DEFAULT_KERNEL_CONFIG.strategySensitivity - 0.3);
    expect(cfg.governanceStrictness).toBeGreaterThan(DEFAULT_KERNEL_CONFIG.governanceStrictness + 0.15);
  });
});

describe("Strategy Gating", () => {
  test("passes through when alignment >= 80", () => {
    const eval90 = mkEvaluation(90, "sovereignty_stable");
    const result = gateStrategyByAlignment(eval90);
    expect(result.name).toBe("sovereignty_stable");
    expect(result.gated).toBeUndefined();
  });

  test("gates to cautious when alignment 60-79", () => {
    const eval70 = mkEvaluation(70, "alignment_nominal");
    const result = gateStrategyByAlignment(eval70);
    expect(result.name).toBe("alignment_guard_cautious");
    expect(result.gated).toBe(true);
    expect(result.originalStrategy).toBe("alignment_nominal");
    expect(result.notes).toContain("gated");
  });

  test("gates to critical when alignment < 60", () => {
    const eval50 = mkEvaluation(50, "governance_undercorrection");
    const result = gateStrategyByAlignment(eval50);
    expect(result.name).toBe("alignment_guard_critical");
    expect(result.gated).toBe(true);
    expect(result.originalStrategy).toBe("governance_undercorrection");
    expect(result.notes).toContain("critical threshold");
  });

  test("alignment exactly at 80 passes through", () => {
    const eval80 = mkEvaluation(80, "alignment_nominal");
    const result = gateStrategyByAlignment(eval80);
    expect(result.name).toBe("alignment_nominal");
  });

  test("alignment exactly at 60 gates to cautious, not critical", () => {
    const eval60 = mkEvaluation(60, "alignment_nominal");
    const result = gateStrategyByAlignment(eval60);
    expect(result.name).toBe("alignment_guard_cautious");
  });

  test("preserves alignment breakdown and confidence through gating", () => {
    const original = mkEvaluation(50, "stability_recovery");
    original.confidence = 72;
    const result = gateStrategyByAlignment(original);
    expect(result.alignment).toBe(50);
    expect(result.confidence).toBe(72);
    expect(result.alignmentBreakdown).toEqual(original.alignmentBreakdown);
  });
});

describe("Posture Selector", () => {
  beforeEach(() => {
    resetSafeMode();
  });

  test("high alignment boosts responsiveness", () => {
    const eval90 = mkEvaluation(90);
    const posture = selectPosture(eval90);
    expect(posture.responsiveness).toBeGreaterThan(DEFAULT_KERNEL_POSTURE.responsiveness);
    expect(posture.caution).toBe(DEFAULT_KERNEL_POSTURE.caution);
  });

  test("low alignment reduces responsiveness and increases caution", () => {
    const eval50 = mkEvaluation(50);
    const posture = selectPosture(eval50);
    expect(posture.responsiveness).toBeLessThan(DEFAULT_KERNEL_POSTURE.responsiveness);
    expect(posture.caution).toBeGreaterThan(DEFAULT_KERNEL_POSTURE.caution);
  });

  test("moderate alignment returns base posture", () => {
    const eval75 = mkEvaluation(75);
    const posture = selectPosture(eval75);
    expect(posture.responsiveness).toBe(DEFAULT_KERNEL_POSTURE.responsiveness);
    expect(posture.caution).toBe(DEFAULT_KERNEL_POSTURE.caution);
  });

  test("posture values are clamped to [0, 1]", () => {
    const evalLow = mkEvaluation(10);
    const posture = selectPosture(evalLow, { responsiveness: 0.1, caution: 0.95 });
    expect(posture.responsiveness).toBeGreaterThanOrEqual(0);
    expect(posture.caution).toBeLessThanOrEqual(1);
  });
});

describe("tickKernel (full pipeline)", () => {
  beforeEach(() => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetSafeMode();
    resetIdentityState();
    resetIntentState();
  });

  test("returns complete tick result", () => {
    const result = tickKernel(mkContext());
    expect(result).toHaveProperty("strategy");
    expect(result).toHaveProperty("posture");
    expect(result).toHaveProperty("config");
    expect(result).toHaveProperty("drift");
    expect(result).toHaveProperty("trend");
    expect(result).toHaveProperty("selfCorrected");
    expect(result).toHaveProperty("escalation");
    expect(result).toHaveProperty("safeMode");
    expect(result).toHaveProperty("intent");
    expect(result.selfCorrected).toBe(false);
    expect(result.intent).toBeNull();
    expect(result.safeMode.active).toBe(false);
  });

  test("strategy has valid structure", () => {
    const result = tickKernel(mkContext());
    expect(result.strategy).toHaveProperty("name");
    expect(result.strategy).toHaveProperty("alignment");
    expect(result.strategy).toHaveProperty("confidence");
    expect(result.strategy).toHaveProperty("alignmentBreakdown");
    expect(result.strategy).toHaveProperty("notes");
  });

  test("posture reflects alignment level", () => {
    const healthy = tickKernel(mkContext());
    expect(healthy.posture.responsiveness).toBeGreaterThanOrEqual(0);
    expect(healthy.posture.caution).toBeGreaterThanOrEqual(0);
  });

  test("records telemetry on each tick", () => {
    tickKernel(mkContext());
    tickKernel(mkContext());
    tickKernel(mkContext());
    const snap = kernelTelemetry.getSnapshot();
    expect(snap.events).toHaveLength(3);
    expect(snap.alignmentHistory).toHaveLength(3);
    expect(snap.drift).toBeDefined();
  });

  test("telemetry snapshot includes drift analysis", () => {
    for (let i = 0; i < 5; i++) tickKernel(mkContext());
    const snap = kernelTelemetry.getSnapshot();
    expect(snap.drift).toHaveProperty("drifting");
    expect(snap.drift).toHaveProperty("delta");
    expect(snap.drift).toHaveProperty("window");
  });

  test("self-correction kicks in with degraded context", () => {
    for (let i = 0; i < 25; i++) {
      tickKernel(mkContext({
        beings: [],
        nodeCount: 0,
        quarantinedCount: 0,
        totalErrors: 50,
        activeHeartbeats: 0,
        constitutionReport: { allPassed: false, failedCount: 5, checks: [] },
        posture: "LOCKDOWN" as PostureState,
        drifts: Array.from({ length: 5 }, (_, j) => ({
          id: `d-${j}`,
          axis: "governance",
          severity: "HIGH" as const,
          detectedAt: new Date().toISOString(),
          description: "test",
          summary: "test",
        })),
      }));
    }
    const result = tickKernel(mkContext({
      beings: [],
      nodeCount: 0,
      constitutionReport: { allPassed: false, failedCount: 5, checks: [] },
      posture: "LOCKDOWN" as PostureState,
    }));
    expect(result.selfCorrected).toBe(true);
    expect(result.config.strategySensitivity).toBeLessThan(DEFAULT_KERNEL_CONFIG.strategySensitivity);
  });

  test("config persists across ticks via service (simulated)", () => {
    let config = { ...DEFAULT_KERNEL_CONFIG };
    for (let i = 0; i < 25; i++) {
      const result = tickKernel(mkContext({
        beings: [],
        nodeCount: 0,
        constitutionReport: { allPassed: false, failedCount: 3, checks: [] },
        posture: "LOCKDOWN" as PostureState,
      }), config);
      config = result.config;
    }
    expect(config.strategySensitivity).toBeLessThan(1.0);
    expect(config.governanceStrictness).toBeGreaterThan(0.8);
  });

  test("strategy gating is applied in the pipeline", () => {
    const result = tickKernel(mkContext({
      beings: [],
      nodeCount: 0,
      quarantinedCount: 0,
      totalErrors: 100,
      activeHeartbeats: 0,
      constitutionReport: { allPassed: false, failedCount: 10, checks: [] },
      posture: "LOCKDOWN" as PostureState,
      drifts: Array.from({ length: 10 }, (_, i) => ({
        id: `d-${i}`,
        axis: "governance",
        severity: "HIGH" as const,
        detectedAt: new Date().toISOString(),
        description: "test",
        summary: "test",
      })),
    }));
    if (result.strategy.alignment < 50) {
      expect(result.strategy.name).toBe("autonomy_paused_alignment_critical");
      expect(result.strategy.gated).toBe(true);
    } else if (result.strategy.alignment < 60) {
      expect(result.strategy.name).toBe("alignment_guard_critical");
      expect(result.strategy.gated).toBe(true);
    } else if (result.strategy.alignment < 80) {
      expect(["alignment_guard_cautious", "alignment_guard_critical"]).toContain(result.strategy.name);
    }
  });

  test("drift detection works end-to-end through telemetry", () => {
    for (let i = 0; i < 5; i++) tickKernel(mkContext());
    const snap = kernelTelemetry.getSnapshot();
    expect(snap.alignmentHistory.length).toBeGreaterThan(0);
    expect(snap.drift).toBeDefined();
    expect(typeof snap.drift.drifting).toBe("boolean");
  });
});
