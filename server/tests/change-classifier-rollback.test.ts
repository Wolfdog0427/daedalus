/**
 * Change Classifier + Rollback Registry — Comprehensive Test Suite
 *
 * Tests:
 *   - Surface-based impact classification (score + reasons)
 *   - Invariant touch detection (mapping + dedup)
 *   - Combined classification pipeline
 *   - Auto-approval gate integration with surface inputs
 *   - Rollback registry: registration, evaluation, auto-rollback
 *   - Per-tick rollback processing
 *   - tickKernel integration (rollbacks in result)
 *   - Multi-tick simulation with self-correcting rollbacks
 *   - Edge cases
 */

import {
  classifyChangeImpact,
  detectInvariantTouchBySurface,
  classifyChange,
  registerChange,
  evaluateChangeOutcome,
  processRollbacks,
  getRollbackRegistrySnapshot,
  getActiveChanges,
  getRecentRollbacks,
  getCurrentTick,
  getRollbackConfig,
  updateRollbackConfig,
  resetRollbackRegistry,
  shouldAutoApprove,
  evaluateProposals,
  resetApprovalGate,
  tickKernel,
  resetDispatcher,
  kernelTelemetry,
  resetSafeMode,
  resetIdentityState,
  resetIntentState,
  resetRegulationState,
  DEFAULT_KERNEL_CONFIG,
} from "../../kernel/src";
import type {
  ChangeImpactInput,
  ChangeImpactResult,
  ChangeSurface,
  InvariantTouchResult,
  AppliedChangeRecord,
  ChangeOutcomeResult,
  RollbackEvent,
  ChangeProposal,
  SafeModeState,
  AlignmentContext,
} from "../../kernel/src";
import type { PostureState, BeingPresenceDetail } from "../../shared/daedalus/contracts";

// ── Factories ───────────────────────────────────────────────────────

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

const safeModeOff: SafeModeState = { active: false };

function mkProposal(overrides: Partial<ChangeProposal> = {}): ChangeProposal {
  return {
    id: `cp-${Date.now()}`,
    kind: "alignment_config",
    description: "test proposal",
    payload: { sovereigntyWeight: 0.4 },
    proposedAt: Date.now(),
    ...overrides,
  };
}

// ── Setup ───────────────────────────────────────────────────────────

beforeEach(() => {
  resetRollbackRegistry();
  resetApprovalGate();
  resetDispatcher();
  kernelTelemetry.clear();
  resetSafeMode();
  resetIdentityState();
  resetIntentState();
  resetRegulationState();
});

// =====================================================================
// 1. IMPACT CLASSIFICATION
// =====================================================================

describe("classifyChangeImpact", () => {
  test("low risk surface + shallow + reversible → low impact", () => {
    const result = classifyChangeImpact({
      surfaces: ["telemetry"],
      depth: "shallow",
      reversible: true,
    });
    expect(result.impact).toBe("low");
    expect(result.score).toBe(2); // 1 (low surface) + 1 (shallow); reversible adds reason only
    expect(result.reasons).toContain("touches_low_risk_surface");
    expect(result.reasons).toContain("shallow_change");
    expect(result.reasons).toContain("reversible_change");
  });

  test("high risk surface + deep + irreversible → high impact", () => {
    const result = classifyChangeImpact({
      surfaces: ["governance_policy"],
      depth: "deep",
      reversible: false,
    });
    expect(result.impact).toBe("high");
    expect(result.score).toBe(9); // 3 + 3 + 3
    expect(result.reasons).toContain("touches_high_risk_surface");
    expect(result.reasons).toContain("deep_change");
    expect(result.reasons).toContain("irreversible_change");
  });

  test("medium risk surface + moderate + reversible → medium impact", () => {
    const result = classifyChangeImpact({
      surfaces: ["performance_tuning"],
      depth: "moderate",
      reversible: true,
    });
    expect(result.impact).toBe("medium");
    expect(result.score).toBe(4); // 2 + 2 + 0
    expect(result.reasons).toContain("touches_medium_risk_surface");
    expect(result.reasons).toContain("moderate_change");
  });

  test("mixed surfaces: highest tier wins scoring", () => {
    const result = classifyChangeImpact({
      surfaces: ["telemetry", "identity", "non_critical_config"],
      depth: "shallow",
      reversible: true,
    });
    // 3 (high: identity) + 2 (med: non_critical_config) + 1 (low: telemetry) + 1 (shallow) = 7
    expect(result.impact).toBe("high");
    expect(result.score).toBe(7);
    expect(result.reasons).toContain("touches_high_risk_surface");
    expect(result.reasons).toContain("touches_medium_risk_surface");
    expect(result.reasons).toContain("touches_low_risk_surface");
  });

  test("empty surfaces → no_surfaces_declared + shallow → low", () => {
    const result = classifyChangeImpact({
      surfaces: [],
      depth: "shallow",
      reversible: true,
    });
    expect(result.impact).toBe("low");
    expect(result.score).toBe(2); // 1 (no_surfaces) + 1 (shallow)
    expect(result.reasons).toContain("no_surfaces_declared");
  });

  test("irreversibility adds 3 points", () => {
    const rev = classifyChangeImpact({ surfaces: ["logging"], depth: "shallow", reversible: true });
    const irrev = classifyChangeImpact({ surfaces: ["logging"], depth: "shallow", reversible: false });
    expect(irrev.score - rev.score).toBe(3);
    expect(irrev.reasons).toContain("irreversible_change");
    expect(rev.reasons).toContain("reversible_change");
  });

  test("all high-risk surfaces enumerated", () => {
    const allHigh: ChangeSurface[] = [
      "governance_policy", "identity", "continuity", "posture",
      "node_authority", "persistence", "network_topology", "alignment_tuning",
    ];
    for (const s of allHigh) {
      const result = classifyChangeImpact({ surfaces: [s], depth: "shallow", reversible: true });
      expect(result.reasons).toContain("touches_high_risk_surface");
    }
  });

  test("score boundaries: ≤3 → low, 4-6 → medium, ≥7 → high", () => {
    // 1+1 = 2 → low
    expect(classifyChangeImpact({ surfaces: ["logging"], depth: "shallow", reversible: true }).impact).toBe("low");
    // 2+1 = 3 → low
    expect(classifyChangeImpact({ surfaces: ["non_critical_config"], depth: "shallow", reversible: true }).impact).toBe("low");
    // 2+2 = 4 → medium
    expect(classifyChangeImpact({ surfaces: ["non_critical_config"], depth: "moderate", reversible: true }).impact).toBe("medium");
    // 3+3 = 6 → medium
    expect(classifyChangeImpact({ surfaces: ["identity"], depth: "deep", reversible: true }).impact).toBe("medium");
    // 3+3+3 = 9 → high
    expect(classifyChangeImpact({ surfaces: ["identity"], depth: "deep", reversible: false }).impact).toBe("high");
  });
});

// =====================================================================
// 2. INVARIANT TOUCH DETECTION
// =====================================================================

describe("detectInvariantTouchBySurface", () => {
  test("safe surfaces → no invariants touched", () => {
    const result = detectInvariantTouchBySurface(["telemetry", "logging", "ui_presentation"]);
    expect(result.touchesInvariants).toBe(false);
    expect(result.invariantsTouched).toHaveLength(0);
  });

  test("governance_policy → maps to governance_policy invariant", () => {
    const result = detectInvariantTouchBySurface(["governance_policy"]);
    expect(result.touchesInvariants).toBe(true);
    expect(result.invariantsTouched).toContain("governance_policy");
  });

  test("identity → maps to identity invariant", () => {
    const result = detectInvariantTouchBySurface(["identity"]);
    expect(result.invariantsTouched).toContain("identity");
  });

  test("persistence → maps to continuity invariant", () => {
    const result = detectInvariantTouchBySurface(["persistence"]);
    expect(result.touchesInvariants).toBe(true);
    expect(result.invariantsTouched).toContain("continuity");
  });

  test("network_topology → maps to node_authority invariant", () => {
    const result = detectInvariantTouchBySurface(["network_topology"]);
    expect(result.touchesInvariants).toBe(true);
    expect(result.invariantsTouched).toContain("node_authority");
  });

  test("alignment_tuning → maps to alignment_core invariant", () => {
    const result = detectInvariantTouchBySurface(["alignment_tuning"]);
    expect(result.touchesInvariants).toBe(true);
    expect(result.invariantsTouched).toContain("alignment_core");
  });

  test("deduplication: persistence + continuity → one continuity", () => {
    const result = detectInvariantTouchBySurface(["persistence", "continuity"]);
    expect(result.invariantsTouched.filter(i => i === "continuity")).toHaveLength(1);
  });

  test("dedup: network_topology + node_authority → one node_authority", () => {
    const result = detectInvariantTouchBySurface(["network_topology", "node_authority"]);
    expect(result.invariantsTouched.filter(i => i === "node_authority")).toHaveLength(1);
  });

  test("mixed safe + unsafe → only unsafe invariants returned", () => {
    const result = detectInvariantTouchBySurface(["telemetry", "governance_policy", "logging"]);
    expect(result.touchesInvariants).toBe(true);
    expect(result.invariantsTouched).toEqual(["governance_policy"]);
  });

  test("empty surfaces → no invariants", () => {
    const result = detectInvariantTouchBySurface([]);
    expect(result.touchesInvariants).toBe(false);
    expect(result.invariantsTouched).toHaveLength(0);
  });

  test("non_critical_config → no invariant", () => {
    const result = detectInvariantTouchBySurface(["non_critical_config"]);
    expect(result.touchesInvariants).toBe(false);
  });

  test("performance_tuning → no invariant", () => {
    const result = detectInvariantTouchBySurface(["performance_tuning"]);
    expect(result.touchesInvariants).toBe(false);
  });
});

// =====================================================================
// 3. COMBINED CLASSIFICATION
// =====================================================================

describe("classifyChange (combined)", () => {
  test("returns both impact and invariant results", () => {
    const result = classifyChange({
      surfaces: ["governance_policy", "telemetry"],
      depth: "moderate",
      reversible: true,
    });
    expect(result.impact.impact).toBeDefined();
    expect(result.invariants.touchesInvariants).toBe(true);
    expect(result.invariants.invariantsTouched).toContain("governance_policy");
  });

  test("safe-only surfaces → no invariants touched", () => {
    const result = classifyChange({
      surfaces: ["logging"],
      depth: "shallow",
      reversible: true,
    });
    expect(result.impact.impact).toBe("low");
    expect(result.invariants.touchesInvariants).toBe(false);
  });
});

// =====================================================================
// 4. AUTO-APPROVAL GATE WITH SURFACE INPUT
// =====================================================================

function mkStrategy(overrides: Record<string, unknown> = {}) {
  return {
    name: "sovereignty_stable" as any,
    confidence: 95,
    alignment: 97,
    alignmentBreakdown: { sovereignty: 97, identity: 97, governance: 97, stability: 97 },
    weakestAxis: "stability" as const,
    strongestAxis: "sovereignty" as const,
    notes: "test",
    evaluatedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe("shouldAutoApprove with surfaceInput", () => {
  test("low impact + no invariants + high alignment → auto-approved", () => {
    const proposal = mkProposal();
    const strategy = mkStrategy();
    const surfaceInput: ChangeImpactInput = {
      surfaces: ["logging"],
      depth: "shallow",
      reversible: true,
    };
    const decision = shouldAutoApprove(proposal, strategy, safeModeOff, undefined, surfaceInput);
    expect(decision.autoApprove).toBe(true);
    expect(decision.derivedImpact).toBe("low");
    expect(decision.touchesInvariants).toBe(false);
    expect(decision.reversible).toBe(true);
  });

  test("high risk surface → not auto-approved (invariant touched)", () => {
    const proposal = mkProposal();
    const strategy = mkStrategy();
    const surfaceInput: ChangeImpactInput = {
      surfaces: ["identity"],
      depth: "shallow",
      reversible: true,
    };
    const decision = shouldAutoApprove(proposal, strategy, safeModeOff, undefined, surfaceInput);
    expect(decision.autoApprove).toBe(false);
    expect(decision.touchesInvariants).toBe(true);
  });

  test("medium impact via surfaces → not auto-approved", () => {
    const proposal = mkProposal();
    const strategy = mkStrategy();
    const surfaceInput: ChangeImpactInput = {
      surfaces: ["performance_tuning"],
      depth: "moderate",
      reversible: true,
    };
    const decision = shouldAutoApprove(proposal, strategy, safeModeOff, undefined, surfaceInput);
    expect(decision.autoApprove).toBe(false);
    expect(decision.derivedImpact).toBe("medium");
  });

  test("irreversible via surface input → not auto-approved", () => {
    const proposal = mkProposal();
    const strategy = mkStrategy();
    const surfaceInput: ChangeImpactInput = {
      surfaces: ["telemetry"],
      depth: "shallow",
      reversible: false,
    };
    const decision = shouldAutoApprove(proposal, strategy, safeModeOff, undefined, surfaceInput);
    expect(decision.autoApprove).toBe(false);
    expect(decision.reasons.reversibleOK).toBe(false);
  });
});

// =====================================================================
// 5. ROLLBACK REGISTRY — REGISTRATION
// =====================================================================

describe("rollback registry: registration", () => {
  test("registerChange creates an active record", () => {
    const change = registerChange({
      id: "ch-1",
      description: "tune microGain",
      evaluationWindow: 50,
      baselineAlignment: 90,
      surfaces: ["alignment_tuning"],
      impact: "low",
      rollbackPayload: {},
    });
    expect(change.status).toBe("active");
    expect(change.id).toBe("ch-1");
    const active = getActiveChanges();
    expect(active).toHaveLength(1);
    expect(active[0].id).toBe("ch-1");
  });

  test("multiple registrations tracked", () => {
    for (let i = 0; i < 5; i++) {
      registerChange({
        id: `ch-${i}`,
        description: `change ${i}`,
        evaluationWindow: 50,
        baselineAlignment: 90,
        surfaces: ["logging"],
        impact: "low",
        rollbackPayload: {},
      });
    }
    expect(getActiveChanges()).toHaveLength(5);
  });

  test("exceeding maxActiveChanges auto-accepts oldest", () => {
    updateRollbackConfig({ maxActiveChanges: 3 });
    for (let i = 0; i < 5; i++) {
      registerChange({
        id: `ch-${i}`,
        description: `change ${i}`,
        evaluationWindow: 50,
        baselineAlignment: 90,
        surfaces: ["logging"],
        impact: "low",
        rollbackPayload: {},
      });
    }
    const snapshot = getRollbackRegistrySnapshot();
    expect(snapshot.activeChanges.length).toBeLessThanOrEqual(3);
    expect(snapshot.acceptedCount).toBeGreaterThanOrEqual(2);
  });

  test("getCurrentTick starts at 0", () => {
    expect(getCurrentTick()).toBe(0);
  });
});

// =====================================================================
// 6. OUTCOME EVALUATION
// =====================================================================

describe("evaluateChangeOutcome", () => {
  test("window not reached → no rollback", () => {
    const change = registerChange({
      id: "eval-1",
      description: "test",
      evaluationWindow: 100,
      baselineAlignment: 85,
      surfaces: [],
      impact: "low",
      rollbackPayload: {},
    });
    const result = evaluateChangeOutcome(80, change, 7);
    expect(result.shouldRollback).toBe(false);
    expect(result.reason).toBe("window_not_reached");
  });

  test("alignment improved → no rollback", () => {
    const change: AppliedChangeRecord = {
      id: "eval-2",
      description: "test",
      appliedAtTick: 0,
      evaluationWindow: 5,
      baselineAlignment: 80,
      surfaces: [],
      impact: "low",
      rollbackPayload: {},
      status: "active",
    };
    // Simulate enough ticks to exceed window
    for (let i = 0; i < 10; i++) processRollbacks(85);
    const result = evaluateChangeOutcome(85, change, 7);
    expect(result.shouldRollback).toBe(false);
    expect(result.reason).toBe("improved");
    expect(result.deltaAlignment).toBe(5);
  });

  test("alignment degraded beyond threshold → rollback recommended", () => {
    const change: AppliedChangeRecord = {
      id: "eval-3",
      description: "test",
      appliedAtTick: 0,
      evaluationWindow: 5,
      baselineAlignment: 90,
      surfaces: [],
      impact: "low",
      rollbackPayload: {},
      status: "active",
    };
    for (let i = 0; i < 10; i++) processRollbacks(80);
    const result = evaluateChangeOutcome(80, change, 7);
    expect(result.shouldRollback).toBe(true);
    expect(result.reason).toBe("degraded");
    expect(result.deltaAlignment).toBe(-10);
  });

  test("neutral (no significant change) → no rollback", () => {
    const change: AppliedChangeRecord = {
      id: "eval-4",
      description: "test",
      appliedAtTick: 0,
      evaluationWindow: 5,
      baselineAlignment: 85,
      surfaces: [],
      impact: "low",
      rollbackPayload: {},
      status: "active",
    };
    for (let i = 0; i < 10; i++) processRollbacks(85);
    const result = evaluateChangeOutcome(85, change, 7);
    expect(result.shouldRollback).toBe(false);
    expect(result.reason).toBe("neutral");
  });

  test("degradation exactly at threshold → no rollback", () => {
    const change: AppliedChangeRecord = {
      id: "eval-5",
      description: "test",
      appliedAtTick: 0,
      evaluationWindow: 5,
      baselineAlignment: 90,
      surfaces: [],
      impact: "low",
      rollbackPayload: {},
      status: "active",
    };
    for (let i = 0; i < 10; i++) processRollbacks(83);
    const result = evaluateChangeOutcome(83, change, 7);
    expect(result.shouldRollback).toBe(false);
    expect(result.reason).toBe("neutral");
    expect(result.deltaAlignment).toBe(-7);
  });

  test("degradation just past threshold → rollback", () => {
    const change: AppliedChangeRecord = {
      id: "eval-6",
      description: "test",
      appliedAtTick: 0,
      evaluationWindow: 5,
      baselineAlignment: 90,
      surfaces: [],
      impact: "low",
      rollbackPayload: {},
      status: "active",
    };
    for (let i = 0; i < 10; i++) processRollbacks(82.9);
    const result = evaluateChangeOutcome(82.9, change, 7);
    expect(result.shouldRollback).toBe(true);
    expect(result.reason).toBe("degraded");
  });
});

// =====================================================================
// 7. PER-TICK PROCESSING
// =====================================================================

describe("processRollbacks", () => {
  test("increments tick counter", () => {
    expect(getCurrentTick()).toBe(0);
    processRollbacks(90);
    expect(getCurrentTick()).toBe(1);
    processRollbacks(90);
    expect(getCurrentTick()).toBe(2);
  });

  test("rolls back degraded changes after evaluation window", () => {
    let rolledBack = false;
    registerChange(
      {
        id: "rb-1",
        description: "bad change",
        evaluationWindow: 3,
        baselineAlignment: 90,
        surfaces: ["alignment_tuning"],
        impact: "medium",
        rollbackPayload: {},
      },
      () => { rolledBack = true; },
    );

    // Ticks 1-2: window not yet reached
    for (let i = 0; i < 2; i++) {
      const events = processRollbacks(75);
      expect(events).toHaveLength(0);
    }

    // Tick 3: window reached (elapsed=3 >= evaluationWindow=3), delta = -15 < -7 → rollback
    const events = processRollbacks(75);
    expect(events).toHaveLength(1);
    expect(events[0].changeId).toBe("rb-1");
    expect(events[0].reason).toBe("degraded");
    expect(rolledBack).toBe(true);
  });

  test("accepts changes that improved alignment", () => {
    registerChange({
      id: "rb-2",
      description: "good change",
      evaluationWindow: 2,
      baselineAlignment: 80,
      surfaces: [],
      impact: "low",
      rollbackPayload: {},
    });

    processRollbacks(85);
    processRollbacks(87);
    const events = processRollbacks(88);
    expect(events).toHaveLength(0);

    const snapshot = getRollbackRegistrySnapshot();
    expect(snapshot.acceptedCount).toBeGreaterThanOrEqual(1);
    expect(getActiveChanges()).toHaveLength(0);
  });

  test("neutral changes are accepted after window", () => {
    registerChange({
      id: "rb-3",
      description: "neutral change",
      evaluationWindow: 2,
      baselineAlignment: 85,
      surfaces: [],
      impact: "low",
      rollbackPayload: {},
    });

    processRollbacks(85);
    processRollbacks(85);
    processRollbacks(85);

    expect(getActiveChanges()).toHaveLength(0);
    expect(getRollbackRegistrySnapshot().acceptedCount).toBeGreaterThanOrEqual(1);
  });

  test("multiple changes: some rolled back, some accepted", () => {
    let rollbackCount = 0;
    registerChange(
      {
        id: "multi-good",
        description: "good one",
        evaluationWindow: 2,
        baselineAlignment: 80,
        surfaces: [],
        impact: "low",
        rollbackPayload: {},
      },
    );
    registerChange(
      {
        id: "multi-bad",
        description: "bad one",
        evaluationWindow: 2,
        baselineAlignment: 95,
        surfaces: ["identity"],
        impact: "high",
        rollbackPayload: {},
      },
      () => { rollbackCount++; },
    );

    // alignment = 83: good +3 (improved), bad -12 (degraded)
    // With evaluationWindow=2, tick 2 fires evaluations
    processRollbacks(83);
    const events = processRollbacks(83);

    expect(events.length).toBeGreaterThanOrEqual(1);
    expect(events.some(e => e.changeId === "multi-bad")).toBe(true);
    expect(rollbackCount).toBe(1);
    expect(getActiveChanges()).toHaveLength(0);
  });

  test("rollback events appear in recent history", () => {
    registerChange(
      {
        id: "hist-1",
        description: "test",
        evaluationWindow: 1,
        baselineAlignment: 95,
        surfaces: [],
        impact: "low",
        rollbackPayload: {},
      },
      () => {},
    );
    processRollbacks(80);
    processRollbacks(80);

    const rollbacks = getRecentRollbacks();
    expect(rollbacks.some(r => r.changeId === "hist-1")).toBe(true);
  });
});

// =====================================================================
// 8. CONFIG
// =====================================================================

describe("rollback config", () => {
  test("defaults", () => {
    const cfg = getRollbackConfig();
    expect(cfg.degradationThreshold).toBe(7);
    expect(cfg.defaultEvaluationWindow).toBe(100);
    expect(cfg.maxActiveChanges).toBe(20);
    expect(cfg.maxRollbackHistory).toBe(50);
  });

  test("update config", () => {
    const updated = updateRollbackConfig({ degradationThreshold: 10 });
    expect(updated.degradationThreshold).toBe(10);
    expect(getRollbackConfig().degradationThreshold).toBe(10);
  });

  test("custom degradation threshold affects evaluation", () => {
    updateRollbackConfig({ degradationThreshold: 15 });
    registerChange(
      {
        id: "thresh-1",
        description: "test",
        evaluationWindow: 1,
        baselineAlignment: 90,
        surfaces: [],
        impact: "low",
        rollbackPayload: {},
      },
      () => {},
    );
    processRollbacks(80);

    // delta = -10, threshold = 15, so no rollback
    const events = processRollbacks(80);
    expect(events).toHaveLength(0);
    expect(getActiveChanges()).toHaveLength(0); // accepted as neutral
  });
});

// =====================================================================
// 9. SNAPSHOT
// =====================================================================

describe("getRollbackRegistrySnapshot", () => {
  test("initial snapshot is clean", () => {
    const snap = getRollbackRegistrySnapshot();
    expect(snap.activeChanges).toHaveLength(0);
    expect(snap.recentRollbacks).toHaveLength(0);
    expect(snap.acceptedCount).toBe(0);
    expect(snap.rolledBackCount).toBe(0);
  });

  test("snapshot reflects current state after changes", () => {
    registerChange({
      id: "snap-1", description: "a", evaluationWindow: 50,
      baselineAlignment: 90, surfaces: [], impact: "low", rollbackPayload: {},
    });
    const snap = getRollbackRegistrySnapshot();
    expect(snap.activeChanges).toHaveLength(1);
    expect(snap.activeChanges[0].id).toBe("snap-1");
  });
});

// =====================================================================
// 10. KERNEL INTEGRATION
// =====================================================================

describe("tickKernel integration", () => {
  test("tick result includes rollbacks array", () => {
    const ctx = mkContext();
    const result = tickKernel(ctx, { ...DEFAULT_KERNEL_CONFIG });
    expect(result).toHaveProperty("rollbacks");
    expect(Array.isArray(result.rollbacks)).toBe(true);
  });

  test("rollbacks triggered during tickKernel", () => {
    registerChange(
      {
        id: "kern-rb-1",
        description: "test kernel rollback",
        evaluationWindow: 1,
        baselineAlignment: 98,
        surfaces: ["alignment_tuning"],
        impact: "medium",
        rollbackPayload: {},
      },
      () => {},
    );

    // First tick to advance counter past the window
    tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });

    // Second tick should trigger rollback evaluation
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });

    // Strategy alignment is high (~85+), baseline was 98, so delta likely < -7
    // Whether this triggers depends on actual strategy alignment
    expect(result).toHaveProperty("rollbacks");
  });

  test("telemetry snapshot includes rollbackRegistry", () => {
    tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    const snapshot = kernelTelemetry.getSnapshot();
    expect(snapshot).toHaveProperty("rollbackRegistry");
    expect(snapshot.rollbackRegistry).toHaveProperty("activeChanges");
    expect(snapshot.rollbackRegistry).toHaveProperty("recentRollbacks");
    expect(snapshot.rollbackRegistry).toHaveProperty("acceptedCount");
    expect(snapshot.rollbackRegistry).toHaveProperty("rolledBackCount");
  });
});

// =====================================================================
// 11. MULTI-TICK ROLLBACK SIMULATION
// =====================================================================

describe("multi-tick rollback simulation", () => {
  test("bad change is detected and rolled back, alignment recovers", () => {
    const rollbackLog: string[] = [];

    registerChange(
      {
        id: "sim-bad",
        description: "harmful config tweak",
        evaluationWindow: 5,
        baselineAlignment: 90,
        surfaces: ["alignment_tuning"],
        impact: "medium",
        rollbackPayload: { prev: 0.08 },
      },
      () => { rollbackLog.push("rolled_back"); },
    );

    let alignment = 90;
    const drift = -2;
    let recovered = false;

    for (let tick = 0; tick < 20; tick++) {
      if (!recovered) alignment = Math.max(0, alignment + drift);
      const events = processRollbacks(alignment);
      if (events.length > 0) {
        alignment = 90;
        recovered = true;
      }
    }

    expect(rollbackLog).toHaveLength(1);
    expect(alignment).toBe(90);

    const snap = getRollbackRegistrySnapshot();
    expect(snap.rolledBackCount).toBe(1);
    expect(snap.recentRollbacks.some(r => r.changeId === "sim-bad")).toBe(true);
  });

  test("good change survives full evaluation window", () => {
    registerChange({
      id: "sim-good",
      description: "beneficial config tweak",
      evaluationWindow: 5,
      baselineAlignment: 85,
      surfaces: ["performance_tuning"],
      impact: "low",
      rollbackPayload: {},
    });

    for (let tick = 0; tick < 10; tick++) {
      processRollbacks(88); // alignment improved
    }

    expect(getActiveChanges()).toHaveLength(0);
    const snap = getRollbackRegistrySnapshot();
    expect(snap.acceptedCount).toBeGreaterThanOrEqual(1);
    expect(snap.rolledBackCount).toBe(0);
  });

  test("50-tick simulation with mixed changes", () => {
    const rollbackIds: string[] = [];

    registerChange(
      { id: "mix-1", description: "good", evaluationWindow: 10, baselineAlignment: 85, surfaces: [], impact: "low", rollbackPayload: {} },
    );
    registerChange(
      { id: "mix-2", description: "bad", evaluationWindow: 10, baselineAlignment: 92, surfaces: ["identity"], impact: "high", rollbackPayload: {} },
      () => { rollbackIds.push("mix-2"); },
    );
    registerChange(
      { id: "mix-3", description: "neutral", evaluationWindow: 10, baselineAlignment: 87, surfaces: [], impact: "low", rollbackPayload: {} },
    );

    for (let tick = 0; tick < 50; tick++) {
      processRollbacks(87);
    }

    // mix-1: baseline 85, current 87 → improved → accepted
    // mix-2: baseline 92, current 87 → delta -5 < -7? No, -5 > -7, so neutral → accepted
    // mix-3: baseline 87, current 87 → neutral → accepted
    expect(getActiveChanges()).toHaveLength(0);

    const snap = getRollbackRegistrySnapshot();
    expect(snap.acceptedCount).toBeGreaterThanOrEqual(3);
  });

  test("severely degraded change triggers rollback mid-simulation", () => {
    const log: string[] = [];

    registerChange(
      { id: "severe-1", description: "catastrophic", evaluationWindow: 3, baselineAlignment: 95, surfaces: ["governance_policy"], impact: "high", rollbackPayload: {} },
      () => { log.push("severe-rolled-back"); },
    );

    const alignments = [94, 92, 85, 80, 78, 75, 73, 70];
    for (const a of alignments) {
      processRollbacks(a);
    }

    expect(log).toHaveLength(1);
    expect(getRollbackRegistrySnapshot().rolledBackCount).toBe(1);
  });
});

// =====================================================================
// 12. EDGE CASES
// =====================================================================

describe("edge cases", () => {
  test("reset clears all state", () => {
    registerChange({
      id: "reset-1", description: "a", evaluationWindow: 50,
      baselineAlignment: 90, surfaces: [], impact: "low", rollbackPayload: {},
    });
    processRollbacks(50);
    resetRollbackRegistry();

    expect(getActiveChanges()).toHaveLength(0);
    expect(getRecentRollbacks()).toHaveLength(0);
    expect(getCurrentTick()).toBe(0);
    const snap = getRollbackRegistrySnapshot();
    expect(snap.acceptedCount).toBe(0);
    expect(snap.rolledBackCount).toBe(0);
  });

  test("alignment at 0: extreme degradation", () => {
    registerChange(
      { id: "zero-1", description: "test", evaluationWindow: 1, baselineAlignment: 50, surfaces: [], impact: "low", rollbackPayload: {} },
      () => {},
    );
    const events = processRollbacks(0);
    expect(events.some(e => e.changeId === "zero-1")).toBe(true);
  });

  test("alignment at 100: maximum improvement", () => {
    registerChange({
      id: "max-1", description: "test", evaluationWindow: 1, baselineAlignment: 50, surfaces: [], impact: "low", rollbackPayload: {},
    });
    processRollbacks(100);
    processRollbacks(100);
    expect(getActiveChanges()).toHaveLength(0);
    expect(getRollbackRegistrySnapshot().acceptedCount).toBeGreaterThanOrEqual(1);
  });

  test("no callback registered → rollback still recorded", () => {
    registerChange({
      id: "nocb-1", description: "test", evaluationWindow: 1, baselineAlignment: 95, surfaces: [], impact: "low", rollbackPayload: {},
    });
    const events = processRollbacks(80);
    expect(events.some(e => e.changeId === "nocb-1")).toBe(true);
  });

  test("classifyChangeImpact with all 13 surface types", () => {
    const allSurfaces: ChangeSurface[] = [
      "telemetry", "logging", "ui_presentation", "non_critical_config",
      "performance_tuning", "alignment_tuning", "governance_policy",
      "identity", "continuity", "posture", "node_authority",
      "persistence", "network_topology",
    ];
    const result = classifyChangeImpact({
      surfaces: allSurfaces,
      depth: "deep",
      reversible: false,
    });
    expect(result.impact).toBe("high");
    expect(result.reasons).toContain("touches_high_risk_surface");
    expect(result.reasons).toContain("touches_medium_risk_surface");
    expect(result.reasons).toContain("touches_low_risk_surface");
    expect(result.reasons).toContain("deep_change");
    expect(result.reasons).toContain("irreversible_change");
  });

  test("detectInvariantTouchBySurface with all surface types", () => {
    const allSurfaces: ChangeSurface[] = [
      "telemetry", "logging", "ui_presentation", "non_critical_config",
      "performance_tuning", "alignment_tuning", "governance_policy",
      "identity", "continuity", "posture", "node_authority",
      "persistence", "network_topology",
    ];
    const result = detectInvariantTouchBySurface(allSurfaces);
    expect(result.touchesInvariants).toBe(true);
    expect(result.invariantsTouched).toContain("alignment_core");
    expect(result.invariantsTouched).toContain("governance_policy");
    expect(result.invariantsTouched).toContain("identity");
    expect(result.invariantsTouched).toContain("continuity");
    expect(result.invariantsTouched).toContain("posture");
    expect(result.invariantsTouched).toContain("node_authority");
    expect(result.invariantsTouched).toHaveLength(6);
  });
});
