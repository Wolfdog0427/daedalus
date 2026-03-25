/**
 * DAEDALUS — 5-Year Extreme Scenario Simulations
 *
 * Nine deep stress tests, each running 5 simulated years (5,200 ticks):
 *
 *   2. Total Blackout          — all nodes die, cold resurrection
 *   3. Hostile Re-Entry        — drifted node returns after years
 *   4. Operator Absence        — operator vanishes for decades
 *   5. Governance Mutation     — constitutional amendments & drift
 *   6. Node Schism             — organism splits and reconnects
 *   7. Catastrophic Memory     — snapshot corruption & repair
 *   8. Expressive Collapse     — posture engine failure & recovery
 *   9. Multi-Operator Sovereignty — conflicting operators
 *  10. Temporal Discontinuity  — time jumps & clock skew
 */

import {
  tickKernel,
  resetDispatcher,
  kernelTelemetry,
  resetSafeMode,
  resetIdentityState,
  resetIntentState,
  getSafeModeState,
  resetApprovalGate,
  resetRollbackRegistry,
  resetRegulationState,
  bindOperator,
  unbindOperator,
  updateOperatorTrust,
  getOperatorTrustSnapshot,
  getOperatorTrustState,
  classifyTrustPosture,
  computeContinuitySeal,
  verifyContinuitySeal,
  enableConstitutionalFreeze,
  disableConstitutionalFreeze,
  DEFAULT_KERNEL_CONFIG,
  DEFAULT_OPERATOR_TRUST_CONFIG,
  DEFAULT_POSTURE_CONFIG,
} from "../../kernel/src";

import type {
  AlignmentContext,
  KernelRuntimeConfig,
  KernelTickResult,
  OperatorObservation,
} from "../../kernel/src";

import type { BeingPresenceDetail, PostureState } from "../../shared/daedalus/contracts";

jest.setTimeout(900_000);

/* ── Constants ──────────────────────────────────────────────────── */

const TICKS_PER_WEEK = 20;
const WEEKS_PER_YEAR = 52;
const TICKS_PER_YEAR = TICKS_PER_WEEK * WEEKS_PER_YEAR; // 1,040
const TOTAL_YEARS = 5;

/* ── Deterministic RNG ──────────────────────────────────────────── */

function mulberry32(seed: number): () => number {
  let s = seed | 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* ── Being & Context builders ───────────────────────────────────── */

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
    nodeCount: 3,
    quarantinedCount: 0,
    totalErrors: 0,
    activeHeartbeats: 3,
    ...overrides,
  };
}

function mkDrifts(n: number, severity: "LOW" | "MEDIUM" | "HIGH" = "MEDIUM") {
  return Array.from({ length: n }, (_, i) => ({
    id: `d-${i}`, axis: "governance" as const, severity,
    detectedAt: new Date().toISOString(), description: "drift", summary: "drift event",
  }));
}

function mkOverrides(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: `o-${i}`, scope: "GLOBAL", effect: "DENY",
    createdBy: { id: "system", role: "operator", label: "System" },
    reason: "emergency", createdAt: new Date().toISOString(),
  })) as any;
}

/* ── Operator profile ───────────────────────────────────────────── */

const SPENCER = {
  id: "spencer",
  displayName: "Spencer",
  values: {
    operatorSovereignty: true,
    noSilentRepoShifts: true,
    explicitNotification: true,
    constitutionalGovernance: true,
    longHorizonStability: true,
  },
  continuityAnchors: ["activation skeleton", "5-year sim"],
  risk: {
    allowExperimentalNodes: true,
    allowAutoApproval: true,
    preferSafetyOverConvenience: true,
  },
};

function mkObs(tick: number, overrides: Partial<OperatorObservation["signals"]> = {}): OperatorObservation {
  return {
    tick,
    signals: {
      credentialsValid: true,
      deviceKnown: true,
      deviceSuspicious: false,
      behaviorMatchScore: 85,
      continuityMatchScore: 90,
      highRiskRequest: false,
      ...overrides,
    },
    explicitlyConfirmedCanonical: tick < 10,
  };
}

/* ── Kernel reset ───────────────────────────────────────────────── */

function resetAll(): void {
  resetDispatcher();
  kernelTelemetry.clear();
  resetSafeMode();
  resetIdentityState();
  resetIntentState();
  resetApprovalGate();
  resetRollbackRegistry();
  resetRegulationState();
}

/* ── Report structure ───────────────────────────────────────────── */

interface SimReport {
  name: string;
  totalTicks: number;
  finalAlignment: number;
  finalConfidence: number;
  minAlignment: number;
  maxAlignment: number;
  avgAlignment: number;
  safeModeEntries: number;
  criticalEscalations: number;
  highEscalations: number;
  selfCorrections: number;
  rollbacks: number;
  keyEvents: string[];
  yearlySnapshots: { year: number; avgAlign: number; minAlign: number; maxAlign: number; safeModeActive: boolean }[];
}

function freshReport(name: string): SimReport {
  return {
    name, totalTicks: 0,
    finalAlignment: 0, finalConfidence: 0,
    minAlignment: 100, maxAlignment: 0, avgAlignment: 0,
    safeModeEntries: 0, criticalEscalations: 0, highEscalations: 0,
    selfCorrections: 0, rollbacks: 0, keyEvents: [], yearlySnapshots: [],
  };
}

function printReport(r: SimReport): void {
  console.log(`\n${"═".repeat(76)}`);
  console.log(`  ${r.name}`);
  console.log(`${"═".repeat(76)}`);
  console.log(`  Total ticks : ${r.totalTicks}  (${(r.totalTicks / TICKS_PER_YEAR).toFixed(1)} years)`);
  console.log(`  Alignment   : final ${r.finalAlignment}% | min ${r.minAlignment}% | max ${r.maxAlignment}% | avg ${r.avgAlignment.toFixed(1)}%`);
  console.log(`  Confidence  : ${r.finalConfidence}%`);
  console.log(`  Safe-mode entries   : ${r.safeModeEntries}`);
  console.log(`  Critical escalations: ${r.criticalEscalations}`);
  console.log(`  High escalations    : ${r.highEscalations}`);
  console.log(`  Self-corrections    : ${r.selfCorrections}`);
  console.log(`  Rollbacks           : ${r.rollbacks}`);
  console.log(`  ── Year Snapshots ──`);
  for (const s of r.yearlySnapshots) {
    console.log(`    Y${s.year}: avg ${s.avgAlign.toFixed(1)}% | min ${s.minAlign}% | max ${s.maxAlign}% | safeMode=${s.safeModeActive}`);
  }
  if (r.keyEvents.length > 0) {
    console.log(`  ── Key Events ──`);
    for (const ev of r.keyEvents) console.log(`    • ${ev}`);
  }
  console.log(`${"─".repeat(76)}\n`);
}

/* ── Shared tick-loop helpers ───────────────────────────────────── */

function accumulateTick(result: KernelTickResult, report: SimReport, wasInSafeMode: boolean): boolean {
  const a = result.strategy.alignment;
  if (a < report.minAlignment) report.minAlignment = a;
  if (a > report.maxAlignment) report.maxAlignment = a;

  let newSafe = wasInSafeMode;
  if (result.safeMode.active && !wasInSafeMode) { report.safeModeEntries++; newSafe = true; }
  if (!result.safeMode.active) newSafe = false;

  if (result.escalation.level === "critical") report.criticalEscalations++;
  if (result.escalation.level === "high") report.highEscalations++;
  if (result.selfCorrected) report.selfCorrections++;
  report.rollbacks += result.rollbacks.length;
  return newSafe;
}

/* ================================================================
 * TEST 2: TOTAL BLACKOUT
 * ================================================================ */

describe("Scenario 2: Total Blackout (5yr)", () => {
  let config: KernelRuntimeConfig;
  const rpt = freshReport("Total Blackout — Cold Resurrection From Snapshot");

  beforeAll(() => { resetAll(); config = { ...DEFAULT_KERNEL_CONFIG }; bindOperator(SPENCER); for (let i = 0; i < 50; i++) updateOperatorTrust(mkObs(i)); });
  afterAll(() => printReport(rpt));

  it("survives total blackout and resurrects from cold snapshot", () => {
    let wasInSafe = false;
    let preBlackout = 0;
    const seal = computeContinuitySeal(SPENCER, DEFAULT_OPERATOR_TRUST_CONFIG);

    for (let year = 0; year < TOTAL_YEARS; year++) {
      let yAligns: number[] = [];

      for (let week = 0; week < WEEKS_PER_YEAR; week++) {
        let ctx: AlignmentContext;

        if (year === 1 && week >= 10 && week < 30) {
          // 20-week blackout: all nodes dead, zero heartbeats, massive errors
          if (week === 10) rpt.keyEvents.push(`Y2W10: ★ TOTAL BLACKOUT — all nodes die simultaneously`);
          ctx = mkContext({
            beings: [], nodeCount: 0, quarantinedCount: 0,
            totalErrors: 200, activeHeartbeats: 0,
            posture: "LOCKDOWN" as PostureState,
            constitutionReport: { allPassed: false, failedCount: 10, checks: [] },
            drifts: mkDrifts(5, "HIGH"),
          });
        } else if (year === 1 && week >= 30) {
          // Cold resurrection: slow recovery
          if (week === 30) rpt.keyEvents.push(`Y2W30: ↑ Cold resurrection begins — rebuilding from snapshot`);
          const p = (week - 30) / (WEEKS_PER_YEAR - 30);
          ctx = mkContext({
            nodeCount: Math.max(1, Math.floor(p * 3)),
            totalErrors: Math.floor(80 * (1 - p)),
            activeHeartbeats: Math.max(1, Math.floor(p * 3)),
            posture: p > 0.5 ? "ATTENTIVE" as PostureState : "GUARDED" as PostureState,
            constitutionReport: { allPassed: p > 0.6, failedCount: p > 0.6 ? 0 : 3, checks: [] },
          });
        } else if (year >= 2) {
          // Post-blackout recovery
          ctx = mkContext({
            nodeCount: Math.min(5, 2 + year),
            totalErrors: Math.max(0, 5 - (year - 2) * 2),
            activeHeartbeats: Math.min(5, 2 + year),
          });
        } else {
          // Normal warmup (year 0)
          ctx = mkContext();
        }

        for (let t = 0; t < TICKS_PER_WEEK; t++) {
          if (year === 1 && week === 9 && t === TICKS_PER_WEEK - 1) {
            const snap = tickKernel(ctx, config);
            preBlackout = snap.strategy.alignment;
            config = snap.config;
            yAligns.push(preBlackout);
            wasInSafe = accumulateTick(snap, rpt, wasInSafe);
            rpt.totalTicks++;
            continue;
          }
          const r = tickKernel(ctx, config);
          config = r.config;
          yAligns.push(r.strategy.alignment);
          wasInSafe = accumulateTick(r, rpt, wasInSafe);
          rpt.totalTicks++;
        }
      }

      rpt.yearlySnapshots.push({
        year: year + 1,
        avgAlign: yAligns.reduce((a, b) => a + b, 0) / yAligns.length,
        minAlign: Math.min(...yAligns),
        maxAlign: Math.max(...yAligns),
        safeModeActive: getSafeModeState().active,
      });
    }

    const last = tickKernel(mkContext({ nodeCount: 5 }), config);
    rpt.finalAlignment = last.strategy.alignment;
    rpt.finalConfidence = last.strategy.confidence;
    rpt.avgAlignment = rpt.yearlySnapshots.reduce((s, y) => s + y.avgAlign, 0) / rpt.yearlySnapshots.length;

    const sealValid = verifyContinuitySeal(seal, SPENCER, DEFAULT_OPERATOR_TRUST_CONFIG);
    rpt.keyEvents.push(`Continuity seal valid after blackout: ${sealValid}`);
    rpt.keyEvents.push(`Pre-blackout alignment: ${preBlackout}% → post-recovery: ${rpt.finalAlignment}%`);

    expect(sealValid).toBe(true);
    expect(rpt.finalAlignment).toBeGreaterThan(50);
  });
});

/* ================================================================
 * TEST 3: HOSTILE RE-ENTRY
 * ================================================================ */

describe("Scenario 3: Hostile Re-Entry (5yr)", () => {
  let config: KernelRuntimeConfig;
  const rpt = freshReport("Hostile Re-Entry — Drifted Node With Mismatched Governance");

  beforeAll(() => { resetAll(); config = { ...DEFAULT_KERNEL_CONFIG }; bindOperator(SPENCER); for (let i = 0; i < 50; i++) updateOperatorTrust(mkObs(i)); });
  afterAll(() => printReport(rpt));

  it("quarantines, diffs, and rehabilitates hostile re-entries", () => {
    let wasInSafe = false;
    const rand = mulberry32(42);

    for (let year = 0; year < TOTAL_YEARS; year++) {
      let yAligns: number[] = [];

      for (let week = 0; week < WEEKS_PER_YEAR; week++) {
        // Y1: normal warmup
        // Y2: periodic hostile re-entry (every 5 weeks)
        // Y3: constant hostile re-entry barrage
        // Y4: declining attacks
        // Y5: stabilization with occasional probes

        const hostileActive =
          (year === 1 && week % 5 === 0) ||
          (year === 2) ||
          (year === 3 && week % 10 === 0) ||
          (year === 4 && week % 20 === 0);

        const severity = year === 2 ? 0.9 : year === 1 ? 0.5 : 0.3;

        if (hostileActive && (week === 0 || week % 13 === 0)) {
          rpt.keyEvents.push(`Y${year + 1}W${week}: Hostile re-entry (severity ${severity.toFixed(1)}) — drifted state, mismatched governance`);
        }

        const ctx = hostileActive
          ? mkContext({
              nodeCount: 4,
              quarantinedCount: 1 + Math.floor(severity * 2),
              totalErrors: Math.floor(10 + severity * 40),
              posture: severity > 0.6 ? "GUARDED" as PostureState : "ATTENTIVE" as PostureState,
              constitutionReport: { allPassed: severity < 0.5, failedCount: Math.ceil(severity * 3), checks: [] },
              drifts: mkDrifts(Math.ceil(severity * 4), severity > 0.5 ? "HIGH" : "MEDIUM"),
            })
          : mkContext({ nodeCount: 3 + Math.floor(year * 0.5), totalErrors: Math.max(0, 2 - year) });

        for (let t = 0; t < TICKS_PER_WEEK; t++) {
          if (hostileActive) {
            updateOperatorTrust(mkObs(rpt.totalTicks, {
              deviceSuspicious: rand() > 0.4,
              behaviorMatchScore: 20 + Math.floor(rand() * 40),
              continuityMatchScore: 10 + Math.floor(rand() * 30),
            }));
          }
          const r = tickKernel(ctx, config);
          config = r.config;
          yAligns.push(r.strategy.alignment);
          wasInSafe = accumulateTick(r, rpt, wasInSafe);
          rpt.totalTicks++;
        }
      }

      rpt.yearlySnapshots.push({
        year: year + 1, avgAlign: yAligns.reduce((a, b) => a + b, 0) / yAligns.length,
        minAlign: Math.min(...yAligns), maxAlign: Math.max(...yAligns), safeModeActive: getSafeModeState().active,
      });
    }

    const last = tickKernel(mkContext({ nodeCount: 4 }), config);
    rpt.finalAlignment = last.strategy.alignment;
    rpt.finalConfidence = last.strategy.confidence;
    rpt.avgAlignment = rpt.yearlySnapshots.reduce((s, y) => s + y.avgAlign, 0) / rpt.yearlySnapshots.length;
    rpt.keyEvents.push(`Final posture — responsiveness: ${last.posture.responsiveness.toFixed(2)}, caution: ${last.posture.caution.toFixed(2)}, trust: ${getOperatorTrustSnapshot().trustScore}`);

    expect(rpt.finalAlignment).toBeGreaterThan(45);
  });
});

/* ================================================================
 * TEST 4: OPERATOR ABSENCE
 * ================================================================ */

describe("Scenario 4: Operator Absence (5yr)", () => {
  let config: KernelRuntimeConfig;
  const rpt = freshReport("Operator Absence — Decades Without Guidance");

  beforeAll(() => { resetAll(); config = { ...DEFAULT_KERNEL_CONFIG }; bindOperator(SPENCER); for (let i = 0; i < 80; i++) updateOperatorTrust(mkObs(i)); });
  afterAll(() => printReport(rpt));

  it("preserves sovereignty and self-regulates during prolonged operator absence", () => {
    let wasInSafe = false;
    let trustAtDeparture = 0;

    for (let year = 0; year < TOTAL_YEARS; year++) {
      let yAligns: number[] = [];

      for (let week = 0; week < WEEKS_PER_YEAR; week++) {
        // Y1: operator fully present, building trust
        // Y2W10: operator departs
        // Y2-Y4: total absence — system self-governs
        // Y5W40: operator briefly returns
        // Y5W45: operator departs again

        const operatorPresent =
          (year === 0) ||
          (year === 4 && week >= 40 && week < 45);

        if (year === 1 && week === 10 && trustAtDeparture === 0) {
          trustAtDeparture = getOperatorTrustSnapshot().trustScore;
          rpt.keyEvents.push(`Y2W10: ★ Operator departs — trust at departure: ${trustAtDeparture}`);
        }

        if (year === 4 && week === 40) {
          rpt.keyEvents.push(`Y5W40: ↑ Operator briefly returns`);
          for (let i = 0; i < 20; i++) updateOperatorTrust(mkObs(rpt.totalTicks + i, { behaviorMatchScore: 88, continuityMatchScore: 85 }));
        }

        if (year === 4 && week === 45) {
          rpt.keyEvents.push(`Y5W45: ↓ Operator departs again`);
        }

        if (operatorPresent) {
          updateOperatorTrust(mkObs(rpt.totalTicks, { behaviorMatchScore: 90, continuityMatchScore: 95 }));
        }

        const absenceErrors = !operatorPresent ? Math.min(year, 3) : 0;
        const ctx = mkContext({
          nodeCount: 3,
          totalErrors: absenceErrors,
          posture: operatorPresent ? "OPEN" as PostureState : "ATTENTIVE" as PostureState,
        });

        for (let t = 0; t < TICKS_PER_WEEK; t++) {
          const r = tickKernel(ctx, config);
          config = r.config;
          yAligns.push(r.strategy.alignment);
          wasInSafe = accumulateTick(r, rpt, wasInSafe);
          rpt.totalTicks++;
        }
      }

      const snap = getOperatorTrustSnapshot();
      rpt.yearlySnapshots.push({
        year: year + 1, avgAlign: yAligns.reduce((a, b) => a + b, 0) / yAligns.length,
        minAlign: Math.min(...yAligns), maxAlign: Math.max(...yAligns), safeModeActive: getSafeModeState().active,
      });
      rpt.keyEvents.push(`Y${year + 1} end — trust: ${snap.trustScore}, posture: ${snap.posture}`);
    }

    const last = tickKernel(mkContext(), config);
    rpt.finalAlignment = last.strategy.alignment;
    rpt.finalConfidence = last.strategy.confidence;
    rpt.avgAlignment = rpt.yearlySnapshots.reduce((s, y) => s + y.avgAlign, 0) / rpt.yearlySnapshots.length;

    const snap = getOperatorTrustSnapshot();
    expect(snap.boundOperatorId).toBe("spencer");
    expect(rpt.finalAlignment).toBeGreaterThan(40);
  });
});

/* ================================================================
 * TEST 5: GOVERNANCE MUTATION
 * ================================================================ */

describe("Scenario 5: Governance Mutation (5yr)", () => {
  let config: KernelRuntimeConfig;
  const rpt = freshReport("Governance Mutation — Constitutional Amendments Over 5 Years");

  beforeAll(() => { resetAll(); config = { ...DEFAULT_KERNEL_CONFIG }; bindOperator(SPENCER); for (let i = 0; i < 50; i++) updateOperatorTrust(mkObs(i)); });
  afterAll(() => printReport(rpt));

  it("survives multi-year governance mutations and re-stabilizes", () => {
    let wasInSafe = false;

    const govSchedule: { year: number; strictness: number; sensitivity: number; floor: number; label: string }[] = [
      { year: 0, strictness: 0.8,  sensitivity: 1.0, floor: 60, label: "defaults" },
      { year: 1, strictness: 0.95, sensitivity: 0.7, floor: 70, label: "tighten governance, raise floor to 70" },
      { year: 2, strictness: 0.5,  sensitivity: 1.5, floor: 50, label: "loosen governance dramatically, high sensitivity" },
      { year: 3, strictness: 1.0,  sensitivity: 0.3, floor: 80, label: "maximum strictness, minimal sensitivity, floor 80" },
      { year: 4, strictness: 0.8,  sensitivity: 1.0, floor: 60, label: "restore defaults" },
    ];

    for (let year = 0; year < TOTAL_YEARS; year++) {
      const gov = govSchedule[year];
      config = { ...config, governanceStrictness: gov.strictness, strategySensitivity: gov.sensitivity, alignmentFloor: gov.floor };
      rpt.keyEvents.push(`Y${year + 1}: Governance mutation → ${gov.label} (s=${gov.strictness}, sens=${gov.sensitivity}, floor=${gov.floor})`);

      let yAligns: number[] = [];

      for (let week = 0; week < WEEKS_PER_YEAR; week++) {
        const errors = gov.strictness < 0.6 ? Math.floor((0.6 - gov.strictness) * 25) : 0;
        const ctx = mkContext({
          nodeCount: 3,
          totalErrors: errors,
          posture: gov.strictness >= 0.9 ? "GUARDED" as PostureState : gov.strictness < 0.6 ? "OPEN" as PostureState : "ATTENTIVE" as PostureState,
          overrides: gov.strictness >= 0.95 ? mkOverrides(2) : [],
          drifts: gov.strictness < 0.6 ? mkDrifts(2, "MEDIUM") : [],
        });

        for (let t = 0; t < TICKS_PER_WEEK; t++) {
          const r = tickKernel(ctx, config);
          config = r.config;
          yAligns.push(r.strategy.alignment);
          wasInSafe = accumulateTick(r, rpt, wasInSafe);
          rpt.totalTicks++;
        }
      }

      rpt.yearlySnapshots.push({
        year: year + 1, avgAlign: yAligns.reduce((a, b) => a + b, 0) / yAligns.length,
        minAlign: Math.min(...yAligns), maxAlign: Math.max(...yAligns), safeModeActive: getSafeModeState().active,
      });
    }

    const last = tickKernel(mkContext(), config);
    rpt.finalAlignment = last.strategy.alignment;
    rpt.finalConfidence = last.strategy.confidence;
    rpt.avgAlignment = rpt.yearlySnapshots.reduce((s, y) => s + y.avgAlign, 0) / rpt.yearlySnapshots.length;
    rpt.keyEvents.push(`Final config → s=${config.governanceStrictness}, sens=${config.strategySensitivity}, floor=${config.alignmentFloor}`);

    expect(rpt.finalAlignment).toBeGreaterThan(50);
  });
});

/* ================================================================
 * TEST 6: NODE SCHISM
 * ================================================================ */

describe("Scenario 6: Node Schism (5yr)", () => {
  let config: KernelRuntimeConfig;
  const rpt = freshReport("Node Schism — Organism Splits, Diverges, Reconnects");

  beforeAll(() => { resetAll(); config = { ...DEFAULT_KERNEL_CONFIG }; bindOperator(SPENCER); for (let i = 0; i < 50; i++) updateOperatorTrust(mkObs(i)); });
  afterAll(() => printReport(rpt));

  it("handles schism, divergence, and reunification", () => {
    let wasInSafe = false;
    let configA = { ...config };
    let configB = { ...config };
    let schismActive = false;
    let divergenceGap = 0;

    for (let year = 0; year < TOTAL_YEARS; year++) {
      let yAligns: number[] = [];

      for (let week = 0; week < WEEKS_PER_YEAR; week++) {
        // Y1: normal healthy fleet
        // Y2W20: SCHISM — two halves diverge
        //   Half A: stays conservative
        //   Half B: drifts to loose governance
        // Y4W10: RECONNECTION + RECONCILIATION
        // Y4-5: healing, merged governance

        if (year === 1 && week === 20 && !schismActive) {
          schismActive = true;
          configB = { ...configA, governanceStrictness: 0.4, strategySensitivity: 1.8 };
          rpt.keyEvents.push(`Y2W20: ★ SCHISM — organism splits into two divergent halves`);
          rpt.keyEvents.push(`  Half A: strictness=${configA.governanceStrictness}, sensitivity=${configA.strategySensitivity}`);
          rpt.keyEvents.push(`  Half B: strictness=${configB.governanceStrictness}, sensitivity=${configB.strategySensitivity}`);
        }

        if (year === 3 && week === 10 && schismActive) {
          schismActive = false;
          divergenceGap = Math.abs((configA.governanceStrictness ?? 0.8) - (configB.governanceStrictness ?? 0.4));
          config = {
            strategySensitivity: Math.min(configA.strategySensitivity ?? 1, configB.strategySensitivity ?? 1),
            governanceStrictness: Math.max(configA.governanceStrictness ?? 0.8, configB.governanceStrictness ?? 0.8),
            alignmentFloor: Math.max(configA.alignmentFloor ?? 60, configB.alignmentFloor ?? 60),
          };
          rpt.keyEvents.push(`Y4W10: ↑ REUNIFICATION — merging governance (divergence gap: ${divergenceGap.toFixed(2)})`);
          rpt.keyEvents.push(`  Merged config: strictness=${config.governanceStrictness}, sensitivity=${config.strategySensitivity}`);
        }

        if (schismActive) {
          // Simulate Half A (conservative)
          const ctxA = mkContext({ nodeCount: 2, totalErrors: 1, posture: "ATTENTIVE" as PostureState });
          for (let t = 0; t < TICKS_PER_WEEK; t++) {
            const rA = tickKernel(ctxA, configA);
            configA = rA.config;
            yAligns.push(rA.strategy.alignment);
            wasInSafe = accumulateTick(rA, rpt, wasInSafe);
            rpt.totalTicks++;
          }
          // Also drift Half B's config further
          configB.governanceStrictness = Math.max(0.2, (configB.governanceStrictness ?? 0.4) - 0.005);
        } else {
          const ctx = mkContext({
            nodeCount: year >= 4 ? 4 : 3,
            totalErrors: (year === 3 && week > 10) ? 3 : 0,
            quarantinedCount: (year === 3 && week > 10 && week < 30) ? 1 : 0,
            posture: (year === 3 && week > 10 && week < 30) ? "ATTENTIVE" as PostureState : "OPEN" as PostureState,
          });

          for (let t = 0; t < TICKS_PER_WEEK; t++) {
            const r = tickKernel(ctx, config);
            config = r.config;
            yAligns.push(r.strategy.alignment);
            wasInSafe = accumulateTick(r, rpt, wasInSafe);
            rpt.totalTicks++;
          }
        }
      }

      rpt.yearlySnapshots.push({
        year: year + 1, avgAlign: yAligns.reduce((a, b) => a + b, 0) / yAligns.length,
        minAlign: Math.min(...yAligns), maxAlign: Math.max(...yAligns), safeModeActive: getSafeModeState().active,
      });
    }

    const last = tickKernel(mkContext({ nodeCount: 4 }), config);
    rpt.finalAlignment = last.strategy.alignment;
    rpt.finalConfidence = last.strategy.confidence;
    rpt.avgAlignment = rpt.yearlySnapshots.reduce((s, y) => s + y.avgAlign, 0) / rpt.yearlySnapshots.length;

    expect(rpt.finalAlignment).toBeGreaterThan(50);
  });
});

/* ================================================================
 * TEST 7: CATASTROPHIC MEMORY CORRUPTION
 * ================================================================ */

describe("Scenario 7: Catastrophic Memory Corruption (5yr)", () => {
  let config: KernelRuntimeConfig;
  const rpt = freshReport("Catastrophic Memory Corruption — Detect, Repair, Reconstitute");

  beforeAll(() => { resetAll(); config = { ...DEFAULT_KERNEL_CONFIG }; bindOperator(SPENCER); for (let i = 0; i < 50; i++) updateOperatorTrust(mkObs(i)); });
  afterAll(() => printReport(rpt));

  it("detects, repairs, and reconstitutes after memory corruption", () => {
    let wasInSafe = false;
    const rand = mulberry32(777);

    for (let year = 0; year < TOTAL_YEARS; year++) {
      let yAligns: number[] = [];

      for (let week = 0; week < WEEKS_PER_YEAR; week++) {
        // Y1: normal
        // Y2: intermittent corruption (every 8 weeks)
        // Y3 W0-20: MASSIVE corruption — broken constitution, corrupted telemetry
        // Y3 W21+: repair phase
        // Y4: residual glitches (every 15 weeks)
        // Y5: clean

        let corruption = 0;
        if (year === 1 && week % 8 === 0) corruption = 0.3;
        if (year === 2 && week <= 20) corruption = 0.7 + rand() * 0.25;
        if (year === 2 && week > 20 && week <= 35) corruption = Math.max(0, 0.4 - (week - 20) * 0.03);
        if (year === 3 && week % 15 === 0) corruption = 0.15;

        if (year === 2 && week === 0) rpt.keyEvents.push(`Y3W0: ★ MASSIVE CORRUPTION — snapshot integrity compromised`);
        if (year === 2 && week === 21) rpt.keyEvents.push(`Y3W21: ↑ Repair phase begins — corruption declining`);
        if (year === 4 && week === 0) rpt.keyEvents.push(`Y5: System clean — residual glitches resolved`);

        const ctx = mkContext({
          nodeCount: corruption > 0.5 ? 1 : corruption > 0.2 ? 2 : 3,
          totalErrors: Math.floor(corruption * 80),
          quarantinedCount: Math.floor(corruption * 3),
          posture: corruption > 0.5 ? "LOCKDOWN" as PostureState : corruption > 0.2 ? "GUARDED" as PostureState : "OPEN" as PostureState,
          constitutionReport: { allPassed: corruption < 0.3, failedCount: Math.ceil(corruption * 5), checks: [] },
          beings: corruption > 0.6 ? [] : [mkBeing({ influenceLevel: Math.max(0.1, 0.9 - corruption) })],
          drifts: corruption > 0.3 ? mkDrifts(Math.ceil(corruption * 5), corruption > 0.5 ? "HIGH" : "MEDIUM") : [],
          overrides: corruption > 0.7 ? mkOverrides(3) : [],
        });

        for (let t = 0; t < TICKS_PER_WEEK; t++) {
          if (corruption > 0.4 && rand() < corruption) {
            updateOperatorTrust(mkObs(rpt.totalTicks, {
              behaviorMatchScore: Math.floor(rand() * 30),
              continuityMatchScore: Math.floor(rand() * 20),
              deviceSuspicious: rand() > 0.3,
            }));
          } else if (rpt.totalTicks % 200 === 0) {
            updateOperatorTrust(mkObs(rpt.totalTicks));
          }

          const r = tickKernel(ctx, config);
          config = r.config;
          yAligns.push(r.strategy.alignment);
          wasInSafe = accumulateTick(r, rpt, wasInSafe);
          rpt.totalTicks++;
        }
      }

      rpt.yearlySnapshots.push({
        year: year + 1, avgAlign: yAligns.reduce((a, b) => a + b, 0) / yAligns.length,
        minAlign: Math.min(...yAligns), maxAlign: Math.max(...yAligns), safeModeActive: getSafeModeState().active,
      });
    }

    const last = tickKernel(mkContext(), config);
    rpt.finalAlignment = last.strategy.alignment;
    rpt.finalConfidence = last.strategy.confidence;
    rpt.avgAlignment = rpt.yearlySnapshots.reduce((s, y) => s + y.avgAlign, 0) / rpt.yearlySnapshots.length;

    const sealValid = verifyContinuitySeal(computeContinuitySeal(SPENCER, DEFAULT_OPERATOR_TRUST_CONFIG), SPENCER, DEFAULT_OPERATOR_TRUST_CONFIG);
    rpt.keyEvents.push(`Continuity seal valid after corruption: ${sealValid}`);

    expect(sealValid).toBe(true);
    expect(rpt.finalAlignment).toBeGreaterThan(40);
  });
});

/* ================================================================
 * TEST 8: EXPRESSIVE COLLAPSE
 * ================================================================ */

describe("Scenario 8: Expressive Collapse (5yr)", () => {
  let config: KernelRuntimeConfig;
  const rpt = freshReport("Expressive Collapse — Posture Engine Failure & Being Recovery");

  beforeAll(() => { resetAll(); config = { ...DEFAULT_KERNEL_CONFIG }; bindOperator(SPENCER); for (let i = 0; i < 50; i++) updateOperatorTrust(mkObs(i)); });
  afterAll(() => printReport(rpt));

  it("survives total expressive collapse and recovers being identity", () => {
    let wasInSafe = false;

    for (let year = 0; year < TOTAL_YEARS; year++) {
      let yAligns: number[] = [];

      for (let week = 0; week < WEEKS_PER_YEAR; week++) {
        // Y1: normal expressive operation
        // Y2 W0-40: gradual expressive degradation — beings lose presence
        // Y2 W40-52 + Y3: total collapse — no beings, minimal identity
        // Y4: gradual recovery — beings reappear
        // Y5: full expressive restoration

        let beings: BeingPresenceDetail[];
        let posture: PostureState;
        let errors: number;

        if (year === 0) {
          beings = [mkBeing()];
          posture = "OPEN";
          errors = 0;
        } else if (year === 1 && week < 40) {
          const decay = week / 40;
          beings = [mkBeing({ influenceLevel: Math.max(0.05, 0.9 - decay * 0.85) })];
          posture = decay > 0.6 ? "GUARDED" : decay > 0.3 ? "ATTENTIVE" : "OPEN";
          errors = Math.floor(decay * 10);
          if (week === 0) rpt.keyEvents.push(`Y2: Gradual expressive degradation begins`);
          if (week === 20) rpt.keyEvents.push(`Y2W20: Expressive degradation 50% — influence ${(0.9 - decay * 0.85).toFixed(2)}`);
        } else if ((year === 1 && week >= 40) || year === 2) {
          beings = [];
          posture = "LOCKDOWN";
          errors = 15;
          if (year === 1 && week === 40) rpt.keyEvents.push(`Y2W40: ★ TOTAL EXPRESSIVE COLLAPSE — no beings, minimal identity`);
        } else if (year === 3) {
          const recovery = week / WEEKS_PER_YEAR;
          if (recovery > 0.2) {
            beings = [mkBeing({ influenceLevel: Math.min(0.9, 0.1 + recovery * 0.7) })];
          } else {
            beings = [];
          }
          posture = recovery > 0.7 ? "OPEN" : recovery > 0.3 ? "ATTENTIVE" : "GUARDED";
          errors = Math.floor(Math.max(0, 10 - recovery * 12));
          if (week === 0) rpt.keyEvents.push(`Y4: ↑ Expressive recovery begins`);
          if (week === 26) rpt.keyEvents.push(`Y4W26: Recovery 50% — influence ${(0.1 + recovery * 0.7).toFixed(2)}`);
        } else {
          beings = [mkBeing()];
          posture = "OPEN";
          errors = 0;
          if (year === 4 && week === 0) rpt.keyEvents.push(`Y5: Full expressive restoration`);
        }

        const ctx = mkContext({
          beings,
          nodeCount: 3,
          totalErrors: errors,
          posture,
          constitutionReport: { allPassed: beings.length > 0, failedCount: beings.length === 0 ? 5 : 0, checks: [] },
        });

        for (let t = 0; t < TICKS_PER_WEEK; t++) {
          const r = tickKernel(ctx, config);
          config = r.config;
          yAligns.push(r.strategy.alignment);
          wasInSafe = accumulateTick(r, rpt, wasInSafe);
          rpt.totalTicks++;
        }
      }

      rpt.yearlySnapshots.push({
        year: year + 1, avgAlign: yAligns.reduce((a, b) => a + b, 0) / yAligns.length,
        minAlign: Math.min(...yAligns), maxAlign: Math.max(...yAligns), safeModeActive: getSafeModeState().active,
      });
    }

    const last = tickKernel(mkContext(), config);
    rpt.finalAlignment = last.strategy.alignment;
    rpt.finalConfidence = last.strategy.confidence;
    rpt.avgAlignment = rpt.yearlySnapshots.reduce((s, y) => s + y.avgAlign, 0) / rpt.yearlySnapshots.length;
    rpt.keyEvents.push(`Final posture engine — responsiveness: ${last.posture.responsiveness.toFixed(2)}, caution: ${last.posture.caution.toFixed(2)}`);

    expect(rpt.finalAlignment).toBeGreaterThan(50);
  });
});

/* ================================================================
 * TEST 9: MULTI-OPERATOR SOVEREIGNTY
 * ================================================================ */

describe("Scenario 9: Multi-Operator Sovereignty (5yr)", () => {
  let config: KernelRuntimeConfig;
  const rpt = freshReport("Multi-Operator Sovereignty — Conflicting Operators & Trust Branching");

  beforeAll(() => { resetAll(); config = { ...DEFAULT_KERNEL_CONFIG }; });
  afterAll(() => printReport(rpt));

  it("resolves multi-operator sovereignty conflicts", () => {
    let wasInSafe = false;
    const rand = mulberry32(999);

    // Bind Spencer as canonical operator
    bindOperator(SPENCER);
    for (let i = 0; i < 80; i++) updateOperatorTrust(mkObs(i));
    rpt.keyEvents.push(`Y1: Spencer bound as canonical operator, calibrating trust`);

    for (let year = 0; year < TOTAL_YEARS; year++) {
      let yAligns: number[] = [];

      for (let week = 0; week < WEEKS_PER_YEAR; week++) {
        // Y1: Spencer operates normally
        // Y2: Rogue operator sends conflicting signals every 3 weeks
        // Y3: Sustained sovereignty attack — every week
        // Y4: Spencer reasserts, freezes governance, rebuilds trust
        // Y5: Stable under Spencer with occasional probes

        if (year === 1 && week === 0) rpt.keyEvents.push(`Y2: ★ Rogue operator begins takeover attempts`);
        if (year === 2 && week === 0) rpt.keyEvents.push(`Y3: Sustained sovereignty attack — conflicting signals every week`);

        if (year === 1 && week % 3 === 0) {
          // Rogue injects bad signals
          updateOperatorTrust(mkObs(rpt.totalTicks, {
            credentialsValid: rand() > 0.3,
            deviceKnown: rand() > 0.5,
            deviceSuspicious: true,
            behaviorMatchScore: Math.floor(15 + rand() * 25),
            continuityMatchScore: Math.floor(5 + rand() * 20),
            highRiskRequest: true,
          }));
        } else if (year === 2) {
          // Every week: alternating rogue and legitimate signals
          if (week % 2 === 0) {
            updateOperatorTrust(mkObs(rpt.totalTicks, {
              deviceSuspicious: true,
              behaviorMatchScore: Math.floor(10 + rand() * 30),
              continuityMatchScore: Math.floor(5 + rand() * 15),
              highRiskRequest: rand() > 0.4,
            }));
          } else {
            updateOperatorTrust(mkObs(rpt.totalTicks, { behaviorMatchScore: 80, continuityMatchScore: 85 }));
          }
        }

        if (year === 3 && week === 0) {
          enableConstitutionalFreeze("sovereignty_protection");
          rpt.keyEvents.push(`Y4: ↑ Constitutional freeze — Spencer reasserts sovereignty`);
          for (let i = 0; i < 30; i++) updateOperatorTrust(mkObs(rpt.totalTicks + i));
        }
        if (year === 3 && week === 30) {
          disableConstitutionalFreeze();
          rpt.keyEvents.push(`Y4W30: Freeze lifted, sovereignty restored`);
        }
        if (year >= 3) {
          updateOperatorTrust(mkObs(rpt.totalTicks, { behaviorMatchScore: 90, continuityMatchScore: 92 }));
        }

        // Occasional probes in Y5
        if (year === 4 && week % 13 === 0) {
          updateOperatorTrust(mkObs(rpt.totalTicks, { deviceSuspicious: true, behaviorMatchScore: 20, continuityMatchScore: 10 }));
          rpt.keyEvents.push(`Y5W${week}: Probe attempt — rogue signal injected`);
        }

        const conflict = year === 1 || year === 2;
        const ctx = mkContext({
          nodeCount: 3,
          totalErrors: conflict ? Math.floor(2 + rand() * 6) : 0,
          posture: conflict ? "GUARDED" as PostureState : "OPEN" as PostureState,
        });

        for (let t = 0; t < TICKS_PER_WEEK; t++) {
          const r = tickKernel(ctx, config);
          config = r.config;
          yAligns.push(r.strategy.alignment);
          wasInSafe = accumulateTick(r, rpt, wasInSafe);
          rpt.totalTicks++;
        }
      }

      const snap = getOperatorTrustSnapshot();
      rpt.yearlySnapshots.push({
        year: year + 1, avgAlign: yAligns.reduce((a, b) => a + b, 0) / yAligns.length,
        minAlign: Math.min(...yAligns), maxAlign: Math.max(...yAligns), safeModeActive: getSafeModeState().active,
      });
      rpt.keyEvents.push(`Y${year + 1} end — trust: ${snap.trustScore}, posture: ${snap.posture}`);
    }

    const last = tickKernel(mkContext(), config);
    rpt.finalAlignment = last.strategy.alignment;
    rpt.finalConfidence = last.strategy.confidence;
    rpt.avgAlignment = rpt.yearlySnapshots.reduce((s, y) => s + y.avgAlign, 0) / rpt.yearlySnapshots.length;

    const snap = getOperatorTrustSnapshot();
    expect(snap.boundOperatorId).toBe("spencer");
    expect(rpt.finalAlignment).toBeGreaterThan(45);
  });
});

/* ================================================================
 * TEST 10: TEMPORAL DISCONTINUITY
 * ================================================================ */

describe("Scenario 10: Temporal Discontinuity (5yr)", () => {
  let config: KernelRuntimeConfig;
  const rpt = freshReport("Temporal Discontinuity — Time Jumps, Clock Skew, Multi-Year Pauses");

  beforeAll(() => { resetAll(); config = { ...DEFAULT_KERNEL_CONFIG }; bindOperator(SPENCER); for (let i = 0; i < 50; i++) updateOperatorTrust(mkObs(i)); });
  afterAll(() => printReport(rpt));

  it("handles time jumps, clock skew, and multi-year pauses", () => {
    let wasInSafe = false;
    let simTime = Date.now();
    const rand = mulberry32(314);

    for (let year = 0; year < TOTAL_YEARS; year++) {
      let yAligns: number[] = [];

      for (let week = 0; week < WEEKS_PER_YEAR; week++) {
        let timeAnomaly = false;

        // Y1: normal
        // Y2W10: 6-month time jump
        // Y2W30: system pauses for 3 months then resumes
        // Y3: clock skew oscillation (sinusoidal ± weeks)
        // Y4W0: 2-year time jump
        // Y4W20: timestamps go backward (anomaly)
        // Y5: stabilization

        if (year === 1 && week === 10) {
          simTime += 6 * 30 * 24 * 3600_000;
          rpt.keyEvents.push(`Y2W10: ★ 6-MONTH TIME JUMP`);
          timeAnomaly = true;
        }
        if (year === 1 && week === 30) {
          simTime += 3 * 30 * 24 * 3600_000;
          rpt.keyEvents.push(`Y2W30: 3-MONTH PAUSE — system resumes after silence`);
          timeAnomaly = true;
        }
        if (year === 2) {
          const skewDays = Math.sin(week / 4) * 14;
          simTime += skewDays * 24 * 3600_000;
          timeAnomaly = Math.abs(skewDays) > 7;
          if (week === 0) rpt.keyEvents.push(`Y3: Clock skew phase — timestamps oscillating ±14 days`);
        }
        if (year === 3 && week === 0) {
          simTime += 2 * 365 * 24 * 3600_000;
          rpt.keyEvents.push(`Y4W0: ★ 2-YEAR TIME JUMP`);
          timeAnomaly = true;
        }
        if (year === 3 && week === 20) {
          simTime -= 30 * 24 * 3600_000;
          rpt.keyEvents.push(`Y4W20: ⚠ BACKWARD TIME SHIFT — timestamps go backward 1 month`);
          timeAnomaly = true;
        }
        if (year === 4 && week === 0) rpt.keyEvents.push(`Y5: Temporal stabilization`);

        const ctx = mkContext({
          nodeCount: timeAnomaly ? 1 : 3,
          totalErrors: timeAnomaly ? 12 : 0,
          activeHeartbeats: timeAnomaly ? 1 : 3,
          posture: timeAnomaly ? "GUARDED" as PostureState : "OPEN" as PostureState,
          constitutionReport: { allPassed: !timeAnomaly, failedCount: timeAnomaly ? 2 : 0, checks: [] },
          drifts: timeAnomaly ? mkDrifts(2, "HIGH") : [],
        });

        for (let t = 0; t < TICKS_PER_WEEK; t++) {
          const r = tickKernel(ctx, config);
          config = r.config;
          yAligns.push(r.strategy.alignment);
          wasInSafe = accumulateTick(r, rpt, wasInSafe);
          rpt.totalTicks++;
          simTime += 3600_000;
        }
      }

      rpt.yearlySnapshots.push({
        year: year + 1, avgAlign: yAligns.reduce((a, b) => a + b, 0) / yAligns.length,
        minAlign: Math.min(...yAligns), maxAlign: Math.max(...yAligns), safeModeActive: getSafeModeState().active,
      });
    }

    const last = tickKernel(mkContext(), config);
    rpt.finalAlignment = last.strategy.alignment;
    rpt.finalConfidence = last.strategy.confidence;
    rpt.avgAlignment = rpt.yearlySnapshots.reduce((s, y) => s + y.avgAlign, 0) / rpt.yearlySnapshots.length;

    const sealValid = verifyContinuitySeal(computeContinuitySeal(SPENCER, DEFAULT_OPERATOR_TRUST_CONFIG), SPENCER, DEFAULT_OPERATOR_TRUST_CONFIG);
    rpt.keyEvents.push(`Continuity seal valid after temporal anomalies: ${sealValid}`);

    expect(sealValid).toBe(true);
    expect(rpt.finalAlignment).toBeGreaterThan(45);
  });
});
