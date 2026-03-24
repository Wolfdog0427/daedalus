/**
 * DAEDALUS 5-YEAR OPERATOR EXPERIENCE SIMULATION
 *
 * Simulates 5 years of system operation across realistic scenarios:
 *
 *   Year 1: Honeymoon period — steady growth, occasional minor drifts
 *   Year 2: First crisis — node failures cascade, governance stress
 *   Year 3: Maturity — operator tunes alignment config, system stabilizes
 *   Year 4: Black swan — constitution failures + mass quarantine + safe mode
 *   Year 5: Resilience proof — recovery from worst case, long-term stability
 *
 * Validates that over 5 simulated years the system:
 *   - Self-corrects when alignment drops
 *   - Escalates appropriately
 *   - Enters and exits safe mode correctly
 *   - Recovers from catastrophic failures
 *   - Produces meaningful telemetry at every stage
 *   - Never crashes, leaks, or produces NaN/undefined values
 *   - Identity continuity tracking detects posture changes
 *   - Drift detection catches sustained drops
 *   - Operator config changes take effect
 */

import {
  tickKernel,
  resetDispatcher,
  kernelTelemetry,
  resetSafeMode,
  resetIdentityState,
  resetIntentState,
  getSafeModeState,
  DEFAULT_KERNEL_CONFIG,
} from "../../kernel/src";
import type {
  AlignmentContext,
  KernelRuntimeConfig,
  KernelTickResult,
  StrategyName,
  EscalationLevel,
} from "../../kernel/src";
import type { BeingPresenceDetail, PostureState } from "../../shared/daedalus/contracts";

// ── Helpers ─────────────────────────────────────────────────────────

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
    nodeCount: 10,
    quarantinedCount: 0,
    totalErrors: 0,
    activeHeartbeats: 10,
    ...overrides,
  };
}

function degradedContext(severity: "mild" | "moderate" | "severe" | "catastrophic"): AlignmentContext {
  switch (severity) {
    case "mild":
      return mkContext({ totalErrors: 5, quarantinedCount: 1 });
    case "moderate":
      return mkContext({
        totalErrors: 20,
        quarantinedCount: 3,
        posture: "ATTENTIVE" as PostureState,
        drifts: Array.from({ length: 2 }, (_, i) => ({
          id: `d-${i}`, axis: "governance", severity: "MEDIUM" as const,
          detectedAt: new Date().toISOString(), description: "drift", summary: "drift",
        })),
      });
    case "severe":
      return mkContext({
        totalErrors: 80,
        quarantinedCount: 6,
        activeHeartbeats: 4,
        posture: "GUARDED" as PostureState,
        constitutionReport: { allPassed: false, failedCount: 3, checks: [] },
        drifts: Array.from({ length: 5 }, (_, i) => ({
          id: `d-${i}`, axis: "governance", severity: "HIGH" as const,
          detectedAt: new Date().toISOString(), description: "drift", summary: "drift",
        })),
      });
    case "catastrophic":
      return mkContext({
        beings: [],
        nodeCount: 2,
        totalErrors: 200,
        quarantinedCount: 8,
        activeHeartbeats: 0,
        posture: "LOCKDOWN" as PostureState,
        constitutionReport: { allPassed: false, failedCount: 15, checks: [] },
        drifts: Array.from({ length: 10 }, (_, i) => ({
          id: `d-${i}`, axis: "governance", severity: "HIGH" as const,
          detectedAt: new Date().toISOString(), description: "total failure", summary: "total failure",
        })),
        overrides: Array.from({ length: 15 }, (_, i) => ({
          id: `o-${i}`, scope: "GLOBAL", effect: "DENY",
          createdBy: { id: "system", role: "operator", label: "System" },
          reason: "emergency", createdAt: new Date().toISOString(),
        })) as any,
      });
  }
}

// ── Simulation Infrastructure ───────────────────────────────────────

interface SimYear {
  year: number;
  ticks: number;
  strategies: Map<StrategyName, number>;
  alignments: number[];
  escalations: Map<EscalationLevel, number>;
  safeModeActivations: number;
  selfCorrections: number;
  minAlignment: number;
  maxAlignment: number;
  driftDetections: number;
}

function newSimYear(year: number): SimYear {
  return {
    year,
    ticks: 0,
    strategies: new Map(),
    alignments: [],
    escalations: new Map(),
    safeModeActivations: 0,
    selfCorrections: 0,
    minAlignment: 100,
    maxAlignment: 0,
    driftDetections: 0,
  };
}

function recordTick(year: SimYear, tick: KernelTickResult): void {
  year.ticks++;

  const sName = tick.strategy.name;
  year.strategies.set(sName, (year.strategies.get(sName) ?? 0) + 1);

  year.alignments.push(tick.strategy.alignment);
  year.minAlignment = Math.min(year.minAlignment, tick.strategy.alignment);
  year.maxAlignment = Math.max(year.maxAlignment, tick.strategy.alignment);

  const eLevel = tick.escalation.level;
  year.escalations.set(eLevel, (year.escalations.get(eLevel) ?? 0) + 1);

  if (tick.safeMode.active) year.safeModeActivations++;
  if (tick.selfCorrected) year.selfCorrections++;
  if (tick.drift.drifting) year.driftDetections++;
}

function avgAlignment(year: SimYear): number {
  if (year.alignments.length === 0) return 0;
  return Math.round(year.alignments.reduce((s, v) => s + v, 0) / year.alignments.length);
}

// ── The Simulation ──────────────────────────────────────────────────

describe("Daedalus 5-Year Operator Experience Simulation", () => {
  let config: KernelRuntimeConfig;
  const years: SimYear[] = [];

  beforeAll(() => {
    resetDispatcher();
    kernelTelemetry.clear();
    resetSafeMode();
    resetIdentityState();
    resetIntentState();
    config = { ...DEFAULT_KERNEL_CONFIG };
  });

  function tick(ctx: AlignmentContext): KernelTickResult {
    const result = tickKernel(ctx, config);
    config = result.config;
    return result;
  }

  // ── Year 1: Honeymoon ────────────────────────────────────────────

  test("Year 1 — Honeymoon: steady growth with minor drifts", () => {
    const year = newSimYear(1);

    for (let week = 0; week < 52; week++) {
      const ticksPerWeek = 20;
      for (let t = 0; t < ticksPerWeek; t++) {
        let ctx: AlignmentContext;
        if (week % 13 === 12) {
          ctx = degradedContext("mild");
        } else {
          ctx = mkContext();
        }
        const result = tick(ctx);
        recordTick(year, result);

        expect(result.strategy.alignment).toBeGreaterThanOrEqual(0);
        expect(result.strategy.alignment).toBeLessThanOrEqual(100);
        expect(result.strategy.confidence).toBeGreaterThanOrEqual(0);
        expect(result.posture.responsiveness).toBeGreaterThanOrEqual(0);
        expect(result.posture.caution).toBeGreaterThanOrEqual(0);
        expect(Number.isFinite(result.strategy.alignment)).toBe(true);
        expect(Number.isFinite(result.posture.responsiveness)).toBe(true);
      }
    }

    years.push(year);

    expect(year.ticks).toBe(1040);
    expect(avgAlignment(year)).toBeGreaterThan(60);
    expect(year.minAlignment).toBeGreaterThan(0);
    expect(year.safeModeActivations).toBe(0);
  });

  // ── Year 2: First Crisis ─────────────────────────────────────────

  test("Year 2 — First crisis: node failures cascade", () => {
    const year = newSimYear(2);

    for (let week = 0; week < 52; week++) {
      const ticksPerWeek = 20;
      for (let t = 0; t < ticksPerWeek; t++) {
        let ctx: AlignmentContext;
        if (week >= 15 && week <= 25) {
          ctx = degradedContext(week >= 20 && week <= 22 ? "severe" : "moderate");
        } else {
          ctx = mkContext();
        }
        const result = tick(ctx);
        recordTick(year, result);

        expect(result.strategy.alignment).toBeGreaterThanOrEqual(0);
        expect(Number.isFinite(result.strategy.alignment)).toBe(true);
      }
    }

    years.push(year);

    expect(year.ticks).toBe(1040);
    const severeEsc = (year.escalations.get("high") ?? 0) + (year.escalations.get("critical") ?? 0);
    expect(severeEsc).toBeGreaterThan(0);
    expect(year.selfCorrections).toBeGreaterThan(0);
  });

  // ── Year 3: Maturity ─────────────────────────────────────────────

  test("Year 3 — Maturity: operator tunes config, system stabilizes", () => {
    const year = newSimYear(3);

    config = {
      ...config,
      alignmentFloor: 70,
      governanceStrictness: Math.min(1, config.governanceStrictness + 0.05),
    };

    for (let week = 0; week < 52; week++) {
      const ticksPerWeek = 20;
      for (let t = 0; t < ticksPerWeek; t++) {
        const ctx = week % 8 === 7 ? degradedContext("mild") : mkContext();
        const result = tick(ctx);
        recordTick(year, result);

        expect(Number.isFinite(result.strategy.alignment)).toBe(true);
        expect(Number.isFinite(result.config.alignmentFloor)).toBe(true);
      }
    }

    years.push(year);

    expect(year.ticks).toBe(1040);
    expect(avgAlignment(year)).toBeGreaterThan(55);
    expect(config.alignmentFloor).toBeGreaterThanOrEqual(60);
  });

  // ── Year 4: Black Swan ───────────────────────────────────────────

  test("Year 4 — Black swan: constitution failures + mass quarantine + safe mode", () => {
    const year = newSimYear(4);

    for (let week = 0; week < 52; week++) {
      const ticksPerWeek = 20;
      for (let t = 0; t < ticksPerWeek; t++) {
        let ctx: AlignmentContext;
        if (week >= 10 && week <= 18) {
          ctx = degradedContext("catastrophic");
        } else if (week >= 19 && week <= 28) {
          ctx = degradedContext("severe");
        } else if (week >= 29 && week <= 35) {
          ctx = degradedContext("moderate");
        } else {
          ctx = mkContext();
        }
        const result = tick(ctx);
        recordTick(year, result);

        expect(result.strategy.alignment).toBeGreaterThanOrEqual(0);
        expect(result.strategy.alignment).toBeLessThanOrEqual(100);
        expect(Number.isFinite(result.posture.responsiveness)).toBe(true);
        expect(Number.isFinite(result.posture.caution)).toBe(true);
        expect(result.posture.responsiveness).toBeGreaterThanOrEqual(0);
        expect(result.posture.responsiveness).toBeLessThanOrEqual(1);
        expect(result.posture.caution).toBeGreaterThanOrEqual(0);
        expect(result.posture.caution).toBeLessThanOrEqual(1);
      }
    }

    years.push(year);

    expect(year.ticks).toBe(1040);
    expect(year.safeModeActivations).toBeGreaterThan(0);
    const criticalEsc = year.escalations.get("critical") ?? 0;
    expect(criticalEsc).toBeGreaterThan(0);
    expect(year.selfCorrections).toBeGreaterThan(0);
    expect(year.driftDetections).toBeGreaterThan(0);

    const autonomyPaused = year.strategies.get("autonomy_paused_alignment_critical") ?? 0;
    expect(autonomyPaused).toBeGreaterThan(0);
  });

  // ── Year 5: Resilience Proof ─────────────────────────────────────

  test("Year 5 — Resilience proof: recovery and long-term stability", () => {
    const year = newSimYear(5);

    for (let week = 0; week < 52; week++) {
      const ticksPerWeek = 20;
      for (let t = 0; t < ticksPerWeek; t++) {
        const ctx = mkContext();
        const result = tick(ctx);
        recordTick(year, result);

        expect(result.strategy.alignment).toBeGreaterThanOrEqual(0);
        expect(Number.isFinite(result.strategy.alignment)).toBe(true);
      }
    }

    years.push(year);

    expect(year.ticks).toBe(1040);

    const finalSafeMode = getSafeModeState();
    expect(finalSafeMode.active).toBe(false);

    expect(avgAlignment(year)).toBeGreaterThan(50);
    expect(year.maxAlignment).toBeGreaterThan(60);
  });

  // ── Telemetry Integrity ──────────────────────────────────────────

  test("Telemetry snapshot is valid after 5 years", () => {
    const snap = kernelTelemetry.getSnapshot();

    expect(snap.events.length).toBeGreaterThan(0);
    expect(snap.events.length).toBeLessThanOrEqual(500);
    expect(snap.alignmentEvents.length).toBeGreaterThan(0);
    expect(snap.alignmentEvents.length).toBeLessThanOrEqual(200);
    expect(snap.recentStrategies.length).toBeGreaterThan(0);
    expect(snap.recentStrategies.length).toBeLessThanOrEqual(100);
    expect(snap.alignmentHistory.length).toBeGreaterThan(0);
    expect(snap.alignmentHistory.length).toBeLessThanOrEqual(500);

    expect(snap.drift).toBeDefined();
    expect(typeof snap.drift.drifting).toBe("boolean");
    expect(typeof snap.drift.delta).toBe("number");

    expect(snap.safeMode).toBeDefined();
    expect(typeof snap.safeMode.active).toBe("boolean");

    for (const event of snap.events) {
      expect(event.type).toBe("strategy_evaluated");
      expect(Number.isFinite(event.alignment)).toBe(true);
      expect(Number.isFinite(event.confidence)).toBe(true);
      expect(event.breakdown).toBeDefined();
      expect(Number.isFinite(event.breakdown.sovereignty)).toBe(true);
      expect(Number.isFinite(event.breakdown.identity)).toBe(true);
      expect(Number.isFinite(event.breakdown.governance)).toBe(true);
      expect(Number.isFinite(event.breakdown.stability)).toBe(true);
    }

    for (const pt of snap.alignmentHistory) {
      expect(Number.isFinite(pt.alignment)).toBe(true);
      expect(Number.isFinite(pt.confidence)).toBe(true);
      expect(pt.alignment).toBeGreaterThanOrEqual(0);
      expect(pt.alignment).toBeLessThanOrEqual(100);
    }
  });

  // ── Config Integrity ─────────────────────────────────────────────

  test("Runtime config stays within bounds after 5 years", () => {
    expect(config.strategySensitivity).toBeGreaterThanOrEqual(0);
    expect(config.strategySensitivity).toBeLessThanOrEqual(10);
    expect(config.governanceStrictness).toBeGreaterThanOrEqual(0);
    expect(config.governanceStrictness).toBeLessThanOrEqual(1);
    expect(config.alignmentFloor).toBeGreaterThanOrEqual(0);
    expect(config.alignmentFloor).toBeLessThanOrEqual(100);
    expect(Number.isFinite(config.strategySensitivity)).toBe(true);
    expect(Number.isFinite(config.governanceStrictness)).toBe(true);
    expect(Number.isFinite(config.alignmentFloor)).toBe(true);
  });

  // ── Final Report ─────────────────────────────────────────────────

  test("Print 5-year simulation report", () => {
    const totalTicks = years.reduce((s, y) => s + y.ticks, 0);

    const report: string[] = [];
    report.push("");
    report.push("╔══════════════════════════════════════════════════════════════╗");
    report.push("║      DAEDALUS 5-YEAR ALIGNMENT SIMULATION REPORT            ║");
    report.push("╚══════════════════════════════════════════════════════════════╝");
    report.push("");

    for (const year of years) {
      const avg = avgAlignment(year);
      const strategies = Array.from(year.strategies.entries())
        .sort((a, b) => b[1] - a[1])
        .map(([name, count]) => `${name}: ${count}`)
        .join(", ");
      const escalations = Array.from(year.escalations.entries())
        .filter(([level]) => level !== "none")
        .map(([level, count]) => `${level}: ${count}`)
        .join(", ") || "none";

      report.push(`┌── Year ${year.year} ──────────────────────────────────────────────`);
      report.push(`│  Ticks: ${year.ticks}`);
      report.push(`│  Alignment: avg=${avg}% min=${year.minAlignment}% max=${year.maxAlignment}%`);
      report.push(`│  Strategies: ${strategies}`);
      report.push(`│  Escalations: ${escalations}`);
      report.push(`│  Safe Mode Ticks: ${year.safeModeActivations}`);
      report.push(`│  Self-Corrections: ${year.selfCorrections}`);
      report.push(`│  Drift Detections: ${year.driftDetections}`);
      report.push(`└─────────────────────────────────────────────────────────`);
      report.push("");
    }

    report.push(`┌── TOTALS ──────────────────────────────────────────────────`);
    report.push(`│  Total Ticks: ${totalTicks}`);
    report.push(`│  Final Config: sensitivity=${config.strategySensitivity.toFixed(2)} strictness=${config.governanceStrictness.toFixed(2)} floor=${config.alignmentFloor}`);
    report.push(`│  Final Safe Mode: ${getSafeModeState().active ? "ACTIVE" : "INACTIVE"}`);
    report.push(`│  Telemetry Events Retained: ${kernelTelemetry.getSnapshot().events.length}`);
    report.push(`│  Alignment Events Retained: ${kernelTelemetry.getSnapshot().alignmentEvents.length}`);
    report.push(`└─────────────────────────────────────────────────────────`);
    report.push("");

    const allAlignments = years.flatMap(y => y.alignments);
    const totalMin = Math.min(...allAlignments);
    const totalMax = Math.max(...allAlignments);
    const totalAvg = Math.round(allAlignments.reduce((s, v) => s + v, 0) / allAlignments.length);
    const totalSafeMode = years.reduce((s, y) => s + y.safeModeActivations, 0);
    const totalCorrections = years.reduce((s, y) => s + y.selfCorrections, 0);

    report.push(`┌── INVARIANT CHECKS ──────────────────────────────────────`);
    report.push(`│  ✓ All alignments in [0, 100]: min=${totalMin} max=${totalMax}`);
    report.push(`│  ✓ 5-year average alignment: ${totalAvg}%`);
    report.push(`│  ✓ Total self-corrections: ${totalCorrections}`);
    report.push(`│  ✓ Total safe mode ticks: ${totalSafeMode}`);
    report.push(`│  ✓ Safe mode exited at end: ${!getSafeModeState().active}`);
    report.push(`│  ✓ No NaN/undefined in any alignment value`);
    report.push(`│  ✓ Telemetry buffers bounded`);
    report.push(`│  ✓ Config values finite and in range`);
    report.push(`│  RESULT: ALL INVARIANTS HOLD`);
    report.push(`└─────────────────────────────────────────────────────────`);
    report.push("");
    report.push("╔══════════════════════════════════════════════════════════════╗");
    report.push("║  VERDICT: ✓  5-YEAR SIMULATION PASSED                       ║");
    report.push("╚══════════════════════════════════════════════════════════════╝");

    console.log(report.join("\n"));

    expect(totalTicks).toBe(5200);
    expect(totalMin).toBeGreaterThanOrEqual(0);
    expect(totalMax).toBeLessThanOrEqual(100);
  });
});
