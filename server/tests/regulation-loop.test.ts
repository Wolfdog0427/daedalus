/**
 * Alignment Regulation Loop — Comprehensive Test Suite
 *
 * Tests:
 *   - Drift metrics computation (magnitude, slope, acceleration)
 *   - Micro-correction layer (continuous homeostasis)
 *   - Macro-correction layer (damped emergency response)
 *   - Governance signals (safe mode enter/exit, autonomy pause/resume)
 *   - Posture modulation from regulation adjustments
 *   - Configurable thresholds and gains
 *   - Integration with tickKernel pipeline
 *   - Edge cases and boundary conditions
 *   - Multi-tick simulation (oscillation damping)
 */

import {
  regulateAlignment,
  runRegulation,
  computeDriftMetrics,
  applyRegulationToPosture,
  getRegulationConfig,
  updateRegulationConfig,
  resetRegulationState,
  tickKernel,
  resetDispatcher,
  kernelTelemetry,
  resetSafeMode,
  resetIdentityState,
  resetIntentState,
  resetApprovalGate,
  DEFAULT_KERNEL_CONFIG,
  DEFAULT_REGULATION_CONFIG,
} from "../../kernel/src";
import type {
  AlignmentHistoryPoint,
  DriftMetrics,
  RegulationConfig,
  RegulationOutput,
  SafeModeState,
  KernelPosture,
  AlignmentContext,
} from "../../kernel/src";
import type { PostureState, BeingPresenceDetail } from "../../shared/daedalus/contracts";

// ── Factories ───────────────────────────────────────────────────────

function mkHistory(alignments: number[], target = 92): AlignmentHistoryPoint[] {
  return alignments.map((a, i) => ({
    timestamp: Date.now() - (alignments.length - i) * 1000,
    strategy: "sovereignty_stable" as any,
    alignment: a,
    confidence: 90,
  }));
}

const safeModeOff: SafeModeState = { active: false };
const safeModeOn: SafeModeState = { active: true, reason: "test", since: Date.now() };

const defaultDrift: DriftMetrics = { magnitude: 0, slope: 0, acceleration: 0 };

function mkBeing(): BeingPresenceDetail {
  return {
    id: "op", label: "Operator", role: "operator",
    presenceMode: "active", isGuiding: true, influenceLevel: 0.9,
    continuity: { healthy: true, streak: 10, lastCheckedAt: new Date().toISOString() },
  } as unknown as BeingPresenceDetail;
}

function mkContext(overrides: Partial<AlignmentContext> = {}): AlignmentContext {
  return {
    beings: [mkBeing()],
    constitutionReport: { allPassed: true, failedCount: 0, checks: [] },
    posture: "OPEN" as PostureState,
    postureReason: "default",
    overrides: [], drifts: [], votes: [],
    nodeCount: 10, quarantinedCount: 0, totalErrors: 0, activeHeartbeats: 10,
    ...overrides,
  };
}

// ── Setup ───────────────────────────────────────────────────────────

beforeEach(() => {
  resetRegulationState();
  resetDispatcher();
  kernelTelemetry.clear();
  resetSafeMode();
  resetIdentityState();
  resetIntentState();
  resetApprovalGate();
});

// ── Drift Metrics Computation ───────────────────────────────────────

describe("computeDriftMetrics", () => {
  test("empty history → zero metrics", () => {
    const m = computeDriftMetrics([], 92);
    expect(m.magnitude).toBe(0);
    expect(m.slope).toBe(0);
    expect(m.acceleration).toBe(0);
  });

  test("single point → magnitude only", () => {
    const m = computeDriftMetrics(mkHistory([80]), 92);
    expect(m.magnitude).toBe(12);
    expect(m.slope).toBe(0);
    expect(m.acceleration).toBe(0);
  });

  test("stable alignment → zero slope and acceleration", () => {
    const m = computeDriftMetrics(mkHistory([85, 85, 85, 85, 85]), 92);
    expect(m.magnitude).toBe(7);
    expect(m.slope).toBe(0);
    expect(m.acceleration).toBe(0);
  });

  test("worsening drift → positive slope", () => {
    const m = computeDriftMetrics(mkHistory([90, 85, 80, 75, 70]), 92);
    expect(m.magnitude).toBe(22);
    expect(m.slope).toBeGreaterThan(0);
  });

  test("improving drift → negative slope", () => {
    const m = computeDriftMetrics(mkHistory([70, 75, 80, 85, 90]), 92);
    expect(m.magnitude).toBe(2);
    expect(m.slope).toBeLessThan(0);
  });

  test("accelerating drift → positive acceleration", () => {
    const m = computeDriftMetrics(mkHistory([90, 89, 86, 81, 74, 65]), 92);
    expect(m.acceleration).toBeGreaterThan(0);
  });

  test("accelerating improvement → negative acceleration", () => {
    const m = computeDriftMetrics(mkHistory([60, 62, 66, 72, 80, 90]), 92);
    expect(m.acceleration).toBeLessThan(0);
  });

  test("alignment at target → zero magnitude", () => {
    const m = computeDriftMetrics(mkHistory([92, 92, 92, 92]), 92);
    expect(m.magnitude).toBe(0);
  });

  test("alignment above target → magnitude still computed", () => {
    const m = computeDriftMetrics(mkHistory([95, 95, 95, 95]), 92);
    expect(m.magnitude).toBe(3);
  });
});

// ── Micro-Correction Layer ──────────────────────────────────────────

describe("Micro-correction layer", () => {
  test("below target → positive micro adjustment", () => {
    const r = regulateAlignment(80, { magnitude: 12, slope: 0, acceleration: 0 }, safeModeOff, false);
    expect(r.microAdjustment).toBeGreaterThan(0);
    expect(r.telemetry.appliedMicro).toBe(true);
  });

  test("above target → negative micro adjustment", () => {
    const r = regulateAlignment(96, { magnitude: 4, slope: 0, acceleration: 0 }, safeModeOff, false);
    expect(r.microAdjustment).toBeLessThan(0);
  });

  test("at target → zero micro adjustment", () => {
    const r = regulateAlignment(92, { magnitude: 0, slope: 0, acceleration: 0 }, safeModeOff, false);
    expect(r.microAdjustment).toBe(0);
    expect(r.telemetry.appliedMicro).toBe(false);
  });

  test("micro is bounded to [-2, 2]", () => {
    const r = regulateAlignment(10, { magnitude: 82, slope: 5, acceleration: 2 }, safeModeOff, false);
    expect(r.microAdjustment).toBeLessThanOrEqual(2);
    expect(r.microAdjustment).toBeGreaterThanOrEqual(-2);
  });

  test("micro scales with magnitude", () => {
    const small = regulateAlignment(88, { magnitude: 4, slope: 0, acceleration: 0 }, safeModeOff, false);
    const large = regulateAlignment(72, { magnitude: 20, slope: 0, acceleration: 0 }, safeModeOff, false);
    expect(Math.abs(large.microAdjustment)).toBeGreaterThan(Math.abs(small.microAdjustment));
  });
});

// ── Macro-Correction Layer ──────────────────────────────────────────

describe("Macro-correction layer", () => {
  test("small drift → no macro", () => {
    const r = regulateAlignment(85, { magnitude: 7, slope: 0, acceleration: 0 }, safeModeOff, false);
    expect(r.macroAdjustment).toBe(0);
    expect(r.telemetry.appliedMacro).toBe(false);
    expect(r.telemetry.reason).toBe("none");
  });

  test("large drift → macro fires", () => {
    const r = regulateAlignment(70, { magnitude: 22, slope: 1, acceleration: 0 }, safeModeOff, false);
    expect(r.macroAdjustment).not.toBe(0);
    expect(r.telemetry.appliedMacro).toBe(true);
    expect(r.telemetry.reason).toBe("large_drift");
  });

  test("accelerating drift → macro fires", () => {
    const r = regulateAlignment(80, { magnitude: 12, slope: 0.5, acceleration: 0.8 }, safeModeOff, false);
    expect(r.macroAdjustment).not.toBe(0);
    expect(r.telemetry.reason).toBe("accelerating_drift");
  });

  test("large AND accelerating → combined reason", () => {
    const r = regulateAlignment(60, { magnitude: 32, slope: 2, acceleration: 1.0 }, safeModeOff, false);
    expect(r.telemetry.reason).toBe("large_and_accelerating_drift");
  });

  test("macro is damped", () => {
    const r = regulateAlignment(70, { magnitude: 22, slope: 1, acceleration: 0 }, safeModeOff, false);
    expect(Math.abs(r.telemetry.macroDampedCorrection)).toBeLessThan(
      Math.abs(r.telemetry.macroRawCorrection),
    );
  });

  test("macro is bounded to [-15, 15]", () => {
    const r = regulateAlignment(5, { magnitude: 87, slope: 5, acceleration: 3 }, safeModeOff, false);
    expect(r.macroAdjustment).toBeLessThanOrEqual(15);
    expect(r.macroAdjustment).toBeGreaterThanOrEqual(-15);
  });

  test("macro direction matches alignment deficit", () => {
    const r = regulateAlignment(60, { magnitude: 32, slope: 2, acceleration: 0 }, safeModeOff, false);
    expect(r.macroAdjustment).toBeGreaterThan(0);
  });
});

// ── Governance Signals ──────────────────────────────────────────────

describe("Governance signals", () => {
  test("catastrophic alignment → shouldEnterSafeMode", () => {
    const r = regulateAlignment(10, { magnitude: 82, slope: 3, acceleration: 1 }, safeModeOff, false);
    expect(r.shouldEnterSafeMode).toBe(true);
  });

  test("critical alignment → shouldPauseAutonomy", () => {
    const r = regulateAlignment(35, { magnitude: 57, slope: 2, acceleration: 0 }, safeModeOff, false);
    expect(r.shouldPauseAutonomy).toBe(true);
  });

  test("already in safe mode → no duplicate enter signal", () => {
    const r = regulateAlignment(10, { magnitude: 82, slope: 3, acceleration: 1 }, safeModeOn, false);
    expect(r.shouldEnterSafeMode).toBe(false);
  });

  test("recovery above floor with improving slope → shouldExitSafeMode", () => {
    const r = regulateAlignment(75, { magnitude: 17, slope: -0.5, acceleration: -0.2 }, safeModeOn, false);
    expect(r.shouldExitSafeMode).toBe(true);
  });

  test("recovery above floor but still worsening → no exit", () => {
    const r = regulateAlignment(75, { magnitude: 17, slope: 0.5, acceleration: 0 }, safeModeOn, false);
    expect(r.shouldExitSafeMode).toBe(false);
  });

  test("autonomy paused + recovery above floor + stable → shouldResumeAutonomy", () => {
    const r = regulateAlignment(80, { magnitude: 12, slope: 0, acceleration: -0.1 }, safeModeOff, true);
    expect(r.shouldResumeAutonomy).toBe(true);
  });

  test("autonomy paused + still accelerating → no resume", () => {
    const r = regulateAlignment(80, { magnitude: 12, slope: 0, acceleration: 0.5 }, safeModeOff, true);
    expect(r.shouldResumeAutonomy).toBe(false);
  });

  test("normal alignment → no governance signals", () => {
    const r = regulateAlignment(90, { magnitude: 2, slope: 0, acceleration: 0 }, safeModeOff, false);
    expect(r.shouldEnterSafeMode).toBe(false);
    expect(r.shouldExitSafeMode).toBe(false);
    expect(r.shouldPauseAutonomy).toBe(false);
    expect(r.shouldResumeAutonomy).toBe(false);
  });
});

// ── Posture Modulation ──────────────────────────────────────────────

describe("Posture modulation", () => {
  const basePosture: KernelPosture = { responsiveness: 0.7, caution: 0.5 };

  test("positive micro → responsiveness increases, caution decreases", () => {
    const reg: RegulationOutput = {
      microAdjustment: 1.5, macroAdjustment: 0,
      shouldEnterSafeMode: false, shouldExitSafeMode: false,
      shouldPauseAutonomy: false, shouldResumeAutonomy: false,
      driftMetrics: defaultDrift,
      telemetry: { appliedMicro: true, appliedMacro: false, macroRawCorrection: 0, macroDampedCorrection: 0, reason: "none" },
    };
    const p = applyRegulationToPosture(basePosture, reg);
    expect(p.responsiveness).toBeGreaterThan(basePosture.responsiveness);
    expect(p.caution).toBeLessThan(basePosture.caution);
  });

  test("no adjustments → posture unchanged", () => {
    const reg: RegulationOutput = {
      microAdjustment: 0, macroAdjustment: 0,
      shouldEnterSafeMode: false, shouldExitSafeMode: false,
      shouldPauseAutonomy: false, shouldResumeAutonomy: false,
      driftMetrics: defaultDrift,
      telemetry: { appliedMicro: false, appliedMacro: false, macroRawCorrection: 0, macroDampedCorrection: 0, reason: "none" },
    };
    const p = applyRegulationToPosture(basePosture, reg);
    expect(p.responsiveness).toBe(basePosture.responsiveness);
    expect(p.caution).toBe(basePosture.caution);
  });

  test("macro adjustment further modulates posture", () => {
    const reg: RegulationOutput = {
      microAdjustment: 1, macroAdjustment: 10,
      shouldEnterSafeMode: false, shouldExitSafeMode: false,
      shouldPauseAutonomy: false, shouldResumeAutonomy: false,
      driftMetrics: defaultDrift,
      telemetry: { appliedMicro: true, appliedMacro: true, macroRawCorrection: 14, macroDampedCorrection: 10, reason: "large_drift" },
    };
    const p = applyRegulationToPosture(basePosture, reg);
    expect(p.responsiveness).toBeGreaterThan(basePosture.responsiveness);
  });

  test("posture stays in [0, 1]", () => {
    const extreme: KernelPosture = { responsiveness: 0.99, caution: 0.01 };
    const reg: RegulationOutput = {
      microAdjustment: 2, macroAdjustment: 15,
      shouldEnterSafeMode: false, shouldExitSafeMode: false,
      shouldPauseAutonomy: false, shouldResumeAutonomy: false,
      driftMetrics: defaultDrift,
      telemetry: { appliedMicro: true, appliedMacro: true, macroRawCorrection: 20, macroDampedCorrection: 15, reason: "large_drift" },
    };
    const p = applyRegulationToPosture(extreme, reg);
    expect(p.responsiveness).toBeLessThanOrEqual(1);
    expect(p.responsiveness).toBeGreaterThanOrEqual(0);
    expect(p.caution).toBeLessThanOrEqual(1);
    expect(p.caution).toBeGreaterThanOrEqual(0);
  });
});

// ── runRegulation (full pipeline) ───────────────────────────────────

describe("runRegulation — full pipeline", () => {
  test("stable history → minimal adjustments", () => {
    const history = mkHistory(Array(20).fill(90));
    const r = runRegulation(history, 90, safeModeOff, false);
    expect(r.microAdjustment).toBeGreaterThan(0);
    expect(r.macroAdjustment).toBe(0);
  });

  test("deteriorating history → micro + macro + governance", () => {
    const vals = Array.from({ length: 30 }, (_, i) => 90 - i * 2);
    const history = mkHistory(vals);
    const current = vals[vals.length - 1];
    const r = runRegulation(history, current, safeModeOff, false);
    expect(r.telemetry.appliedMicro).toBe(true);
    expect(r.telemetry.appliedMacro).toBe(true);
    expect(r.shouldPauseAutonomy).toBe(true);
  });

  test("empty history → safe defaults", () => {
    const r = runRegulation([], 92, safeModeOff, false);
    expect(r.microAdjustment).toBe(0);
    expect(r.macroAdjustment).toBe(0);
    expect(r.driftMetrics.magnitude).toBe(0);
  });
});

// ── Configurable Thresholds ─────────────────────────────────────────

describe("Configurable thresholds", () => {
  test("defaults match constants", () => {
    const cfg = getRegulationConfig();
    expect(cfg.targetAlignment).toBe(92);
    expect(cfg.floorAlignment).toBe(70);
    expect(cfg.microGain).toBe(0.08);
    expect(cfg.macroGain).toBe(0.5);
    expect(cfg.macroDamping).toBe(0.7);
    expect(cfg.macroDriftThreshold).toBe(18);
    expect(cfg.macroAccelerationThreshold).toBe(0.6);
    expect(cfg.criticalAlignmentThreshold).toBe(40);
    expect(cfg.catastrophicAlignmentThreshold).toBe(15);
  });

  test("update config affects regulation behavior", () => {
    updateRegulationConfig({ macroDriftThreshold: 5 });
    const r = regulateAlignment(85, { magnitude: 7, slope: 0, acceleration: 0 }, safeModeOff, false);
    expect(r.telemetry.appliedMacro).toBe(true);
  });

  test("higher micro gain → stronger micro adjustment", () => {
    const low = regulateAlignment(
      80, { magnitude: 12, slope: 0, acceleration: 0 }, safeModeOff, false,
      { ...DEFAULT_REGULATION_CONFIG, microGain: 0.05 },
    );
    const high = regulateAlignment(
      80, { magnitude: 12, slope: 0, acceleration: 0 }, safeModeOff, false,
      { ...DEFAULT_REGULATION_CONFIG, microGain: 0.15 },
    );
    expect(Math.abs(high.microAdjustment)).toBeGreaterThan(Math.abs(low.microAdjustment));
  });

  test("higher macro damping → smaller damped correction", () => {
    const lowDamp = regulateAlignment(
      60, { magnitude: 32, slope: 2, acceleration: 0 }, safeModeOff, false,
      { ...DEFAULT_REGULATION_CONFIG, macroDamping: 0.3 },
    );
    const highDamp = regulateAlignment(
      60, { magnitude: 32, slope: 2, acceleration: 0 }, safeModeOff, false,
      { ...DEFAULT_REGULATION_CONFIG, macroDamping: 0.9 },
    );
    expect(Math.abs(lowDamp.macroAdjustment)).toBeLessThan(Math.abs(highDamp.macroAdjustment));
  });

  test("reset restores defaults", () => {
    updateRegulationConfig({ targetAlignment: 50 });
    resetRegulationState();
    expect(getRegulationConfig().targetAlignment).toBe(92);
  });
});

// ── tickKernel Integration ──────────────────────────────────────────

describe("tickKernel integration", () => {
  test("tick includes regulation output", () => {
    const result = tickKernel(mkContext());
    expect(result.regulation).toBeDefined();
    expect(typeof result.regulation.microAdjustment).toBe("number");
    expect(typeof result.regulation.macroAdjustment).toBe("number");
    expect(result.regulation.driftMetrics).toBeDefined();
    expect(result.regulation.telemetry).toBeDefined();
  });

  test("posture is modulated by regulation", () => {
    for (let i = 0; i < 5; i++) {
      tickKernel(mkContext());
    }
    const result = tickKernel(mkContext());
    expect(result.posture.responsiveness).toBeGreaterThanOrEqual(0);
    expect(result.posture.caution).toBeGreaterThanOrEqual(0);
    expect(result.posture.responsiveness).toBeLessThanOrEqual(1);
    expect(result.posture.caution).toBeLessThanOrEqual(1);
  });

  test("telemetry snapshot includes last regulation", () => {
    tickKernel(mkContext());
    const snap = kernelTelemetry.getSnapshot();
    expect(snap.lastRegulation).toBeDefined();
  });

  test("regulation uses alignment history from telemetry", () => {
    for (let i = 0; i < 10; i++) {
      tickKernel(mkContext());
    }
    const result = tickKernel(mkContext());
    expect(result.regulation.driftMetrics.magnitude).toBeGreaterThanOrEqual(0);
  });
});

// ── Multi-tick Simulation (oscillation damping) ─────────────────────

describe("Multi-tick oscillation damping simulation", () => {
  test("micro-corrections keep alignment stable over 50 ticks", () => {
    const alignments: number[] = [];

    for (let i = 0; i < 50; i++) {
      const result = tickKernel(mkContext());
      alignments.push(result.strategy.alignment);
    }

    const maxSwing = Math.max(...alignments) - Math.min(...alignments);
    expect(maxSwing).toBeLessThan(50);

    for (const a of alignments) {
      expect(a).toBeGreaterThanOrEqual(0);
      expect(a).toBeLessThanOrEqual(100);
    }
  });

  test("regulation output is always finite", () => {
    for (let i = 0; i < 30; i++) {
      const result = tickKernel(mkContext());
      expect(Number.isFinite(result.regulation.microAdjustment)).toBe(true);
      expect(Number.isFinite(result.regulation.macroAdjustment)).toBe(true);
      expect(Number.isFinite(result.regulation.driftMetrics.magnitude)).toBe(true);
      expect(Number.isFinite(result.regulation.driftMetrics.slope)).toBe(true);
      expect(Number.isFinite(result.regulation.driftMetrics.acceleration)).toBe(true);
    }
  });
});

// ── Edge Cases ──────────────────────────────────────────────────────

describe("Edge cases", () => {
  test("alignment exactly at catastrophic threshold", () => {
    const r = regulateAlignment(15, { magnitude: 77, slope: 2, acceleration: 1 }, safeModeOff, false);
    expect(r.shouldEnterSafeMode).toBe(true);
    expect(r.shouldPauseAutonomy).toBe(true);
  });

  test("alignment exactly at critical threshold", () => {
    const r = regulateAlignment(40, { magnitude: 52, slope: 1, acceleration: 0 }, safeModeOff, false);
    expect(r.shouldPauseAutonomy).toBe(true);
    expect(r.shouldEnterSafeMode).toBe(false);
  });

  test("alignment at 0 → max governance response", () => {
    const r = regulateAlignment(0, { magnitude: 92, slope: 5, acceleration: 3 }, safeModeOff, false);
    expect(r.shouldEnterSafeMode).toBe(true);
    expect(r.shouldPauseAutonomy).toBe(true);
    expect(r.telemetry.appliedMacro).toBe(true);
    expect(r.macroAdjustment).toBe(15);
  });

  test("alignment at 100 → negative micro (toward 92 target)", () => {
    const r = regulateAlignment(100, { magnitude: 8, slope: 0, acceleration: 0 }, safeModeOff, false);
    expect(r.microAdjustment).toBeLessThan(0);
  });

  test("drift magnitude at exact macro threshold", () => {
    const r = regulateAlignment(74, { magnitude: 18, slope: 0, acceleration: 0 }, safeModeOff, false);
    expect(r.telemetry.appliedMacro).toBe(true);
  });

  test("acceleration at exact threshold", () => {
    const r = regulateAlignment(82, { magnitude: 10, slope: 0.3, acceleration: 0.6 }, safeModeOff, false);
    expect(r.telemetry.appliedMacro).toBe(true);
  });

  test("two points in history → slope computed, acceleration zero", () => {
    const m = computeDriftMetrics(mkHistory([90, 80]), 92);
    expect(m.slope).not.toBe(0);
    expect(m.acceleration).toBe(0);
  });
});
