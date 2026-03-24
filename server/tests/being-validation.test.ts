/**
 * Daedalus Being Validation — Orthogonal Dimension Test Suite
 *
 * Validates the system from every angle:
 *   D3: Kernel pipeline integrity (tickKernel result shape, all fields present)
 *   D4: State management (reset, isolation, module consistency)
 *   D5: Cross-module composition (auto-approval + regulation + rollback + operator trust)
 *   D6: Telemetry snapshot completeness (every field, no undefined leaks)
 *   D7: Cross-module invariant enforcement
 *   D9: Edge cases + adversarial inputs
 */

import {
  tickKernel,
  kernelTelemetry,
  resetDispatcher,
  resetSafeMode,
  resetIdentityState,
  resetIntentState,
  resetApprovalGate,
  resetRegulationState,
  resetRollbackRegistry,
  resetOperatorIdentity,
  bindOperator,
  unbindOperator,
  updateOperatorTrust,
  classifyTrustPosture,
  deriveComfortPosture,
  isHighRiskAction,
  getOperatorTrustSnapshot,
  getOperatorTrustState,
  enableConstitutionalFreeze,
  disableConstitutionalFreeze,
  getConstitutionalFreezeState,
  enforceConstitutionalFreeze,
  enforceNoSilentDrift,
  computeContinuitySeal,
  verifyContinuitySeal,
  runSelfAudit,
  startAttunement,
  advanceAttunement,
  getAttunementState,
  recordTrustDriftSample,
  getTrustDriftSamples,
  buildWeeklyTrustNarrative,
  addRelationshipEvent,
  getRelationshipTimeline,
  getRecentHighRiskLog,
  buildHighRiskDecisionLog,
  buildComfortLayerView,
  introspectPosture,
  introspectHighRiskDecision,
  runRedTeamScenario,
  runFutureYouSanityCheck,
  shouldAutoApprove,
  evaluateProposals,
  getApprovalGateConfig,
  getRecentApprovalDecisions,
  classifyChangeImpact,
  detectInvariantTouchBySurface,
  classifyChange,
  registerChange,
  processRollbacks,
  getRollbackRegistrySnapshot,
  getActiveChanges,
  regulateAlignment,
  runRegulation,
  computeDriftMetrics,
  getRegulationConfig,
  getLastRegulationOutput,
  getSafeModeState,
  computeRecentAlignmentTrend,
  selectStrategy,
  detectAlignmentDrift,
  computeAlignmentEscalation,
  interpretIntent,
  computeIdentityContinuity,
  selectPosture,
  DEFAULT_KERNEL_CONFIG,
  DEFAULT_ALIGNMENT_CONFIG,
  DEFAULT_OPERATOR_TRUST_CONFIG,
  DEFAULT_POSTURE_CONFIG,
  DEFAULT_REGULATION_CONFIG,
  DEFAULT_ROLLBACK_CONFIG,
  DEFAULT_APPROVAL_GATE_CONFIG,
  INITIAL_OPERATOR_TRUST_STATE,
  HIGH_RISK_ACTIONS,
} from "../../kernel/src";
import type {
  AlignmentContext,
  StrategyEvaluation,
  KernelTickResult,
  KernelTelemetrySnapshot,
  ChangeProposal,
  OperatorProfile,
  OperatorObservation,
  OperatorTrustCockpitSnapshot,
  ChangeImpactInput,
} from "../../kernel/src";
import type { PostureState, BeingPresenceDetail } from "../../shared/daedalus/contracts";

// ── Factories ─────────────────────────────────────────────────────

const spencerProfile: OperatorProfile = {
  id: "spencer",
  displayName: "Spencer",
  values: {
    operatorSovereignty: true,
    noSilentRepoShifts: true,
    explicitNotification: true,
    constitutionalGovernance: true,
    longHorizonStability: true,
  },
  continuityAnchors: ["activation skeleton", "1,442 tests", "250-year sim"],
  risk: {
    allowExperimentalNodes: true,
    allowAutoApproval: true,
    preferSafetyOverConvenience: true,
  },
};

function mkBeing(): BeingPresenceDetail {
  return {
    id: "op", label: "Operator", role: "operator",
    presenceMode: "active", isGuiding: true, influenceLevel: 0.9,
    continuity: { healthy: true, streak: 10, lastCheckedAt: new Date().toISOString() },
  } as unknown as BeingPresenceDetail;
}

function mkContext(overrides?: Partial<AlignmentContext>): AlignmentContext {
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

function mkObs(tick: number, overrides: Partial<OperatorObservation["signals"]> = {}, canonical = false): OperatorObservation {
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
    explicitlyConfirmedCanonical: canonical,
  };
}

function mkProposal(kind = "alignment_config" as const, desc = "test proposal"): ChangeProposal {
  return {
    id: `proposal-${Date.now()}-${Math.random()}`,
    kind,
    description: desc,
    payload: {},
    proposedAt: Date.now(),
  };
}

function resetAll() {
  resetDispatcher();
  kernelTelemetry.clear();
  resetSafeMode();
  resetIdentityState();
  resetIntentState();
  resetApprovalGate();
  resetRegulationState();
  resetRollbackRegistry();
  resetOperatorIdentity();
}

beforeEach(resetAll);

// =====================================================================
// D3: KERNEL PIPELINE INTEGRITY
// =====================================================================

describe("D3: Kernel pipeline integrity", () => {
  test("tickKernel returns all required fields", () => {
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });

    expect(result).toHaveProperty("strategy");
    expect(result).toHaveProperty("posture");
    expect(result).toHaveProperty("config");
    expect(result).toHaveProperty("drift");
    expect(result).toHaveProperty("trend");
    expect(result).toHaveProperty("selfCorrected");
    expect(result).toHaveProperty("escalation");
    expect(result).toHaveProperty("safeMode");
    expect(result).toHaveProperty("intent");
    expect(result).toHaveProperty("approvals");
    expect(result).toHaveProperty("regulation");
    expect(result).toHaveProperty("rollbacks");
    expect(result).toHaveProperty("operatorTrust");
  });

  test("strategy result has all alignment fields", () => {
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    const s = result.strategy;

    expect(typeof s.name).toBe("string");
    expect(typeof s.alignment).toBe("number");
    expect(typeof s.confidence).toBe("number");
    expect(s.alignmentBreakdown).toBeDefined();
    expect(typeof s.alignmentBreakdown.sovereignty).toBe("number");
    expect(typeof s.alignmentBreakdown.identity).toBe("number");
    expect(typeof s.alignmentBreakdown.governance).toBe("number");
    expect(typeof s.alignmentBreakdown.stability).toBe("number");
  });

  test("posture result has responsiveness and caution", () => {
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    expect(typeof result.posture.responsiveness).toBe("number");
    expect(typeof result.posture.caution).toBe("number");
    expect(result.posture.responsiveness).toBeGreaterThanOrEqual(0);
    expect(result.posture.caution).toBeGreaterThanOrEqual(0);
  });

  test("regulation output has all fields", () => {
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    const r = result.regulation;

    expect(typeof r.microAdjustment).toBe("number");
    expect(typeof r.macroAdjustment).toBe("number");
    expect(typeof r.shouldEnterSafeMode).toBe("boolean");
    expect(typeof r.shouldExitSafeMode).toBe("boolean");
    expect(typeof r.shouldPauseAutonomy).toBe("boolean");
    expect(typeof r.shouldResumeAutonomy).toBe("boolean");
    expect(r.driftMetrics).toBeDefined();
    expect(r.telemetry).toBeDefined();
    expect(typeof r.telemetry.appliedMicro).toBe("boolean");
    expect(typeof r.telemetry.appliedMacro).toBe("boolean");
  });

  test("operator trust snapshot in tick result has all fields", () => {
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    const ot = result.operatorTrust;

    expect(ot).toHaveProperty("boundOperatorId");
    expect(ot).toHaveProperty("boundOperatorName");
    expect(ot).toHaveProperty("posture");
    expect(ot).toHaveProperty("comfortPosture");
    expect(ot).toHaveProperty("trustScore");
    expect(ot).toHaveProperty("axes");
    expect(ot).toHaveProperty("calibrated");
    expect(ot).toHaveProperty("narrative");
    expect(ot).toHaveProperty("freeze");
    expect(ot).toHaveProperty("recentHighRiskDecisions");
  });

  test("multiple ticks produce stable pipeline", () => {
    const config = { ...DEFAULT_KERNEL_CONFIG };
    const ctx = mkContext();

    for (let i = 0; i < 20; i++) {
      const result = tickKernel(ctx, config);
      expect(result.strategy.alignment).toBeGreaterThanOrEqual(0);
      expect(result.strategy.alignment).toBeLessThanOrEqual(100);
    }
  });

  test("tickKernel with intent input", () => {
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG }, { raw: "check governance status" });
    expect(result.intent).not.toBeNull();
    expect(result.intent!.action).toBeDefined();
    expect(typeof result.intent!.strictness).toBe("number");
  });

  test("tickKernel with change proposals", () => {
    tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    const proposals = [mkProposal()];
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG }, undefined, proposals);
    expect(result.approvals).toHaveLength(1);
    expect(result.approvals[0]).toHaveProperty("autoApprove");
    expect(result.approvals[0]).toHaveProperty("reasons");
    expect(result.approvals[0]).toHaveProperty("derivedImpact");
  });

  test("rollbacks field is always an array", () => {
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    expect(Array.isArray(result.rollbacks)).toBe(true);
  });
});

// =====================================================================
// D4: STATE MANAGEMENT
// =====================================================================

describe("D4: State management", () => {
  test("resetAll clears all module state", () => {
    tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    bindOperator(spencerProfile);
    for (let t = 1; t <= 5; t++) updateOperatorTrust(mkObs(t, {}, true));
    enableConstitutionalFreeze("test");
    startAttunement();
    recordTrustDriftSample(1);
    addRelationshipEvent({ tick: 1, kind: "milestone", title: "Test", description: "" });

    resetAll();

    expect(getOperatorTrustState().boundOperator).toBeNull();
    expect(getConstitutionalFreezeState().frozen).toBe(false);
    expect(getTrustDriftSamples()).toHaveLength(0);
    expect(getAttunementState()).toBeNull();
    expect(getRelationshipTimeline().events).toHaveLength(0);
    expect(getRecentHighRiskLog()).toHaveLength(0);
    expect(getSafeModeState().active).toBe(false);
    expect(getRecentApprovalDecisions()).toHaveLength(0);
    expect(getLastRegulationOutput()).toBeNull();
    expect(getRollbackRegistrySnapshot().activeChanges).toHaveLength(0);
  });

  test("test isolation: successive tests start fresh", () => {
    expect(getOperatorTrustState().boundOperator).toBeNull();
    expect(getOperatorTrustState().trustScore).toBe(0);
  });

  test("operator trust state returns defensive copies", () => {
    bindOperator(spencerProfile);
    const s1 = getOperatorTrustState();
    s1.trustScore = 999;
    s1.axes.credentials = 999;
    const s2 = getOperatorTrustState();
    expect(s2.trustScore).toBe(0);
    expect(s2.axes.credentials).toBe(0);
  });

  test("operator trust snapshot returns defensive copies", () => {
    bindOperator(spencerProfile);
    const snap1 = getOperatorTrustSnapshot();
    (snap1 as any).trustScore = 999;
    const snap2 = getOperatorTrustSnapshot();
    expect(snap2.trustScore).toBe(0);
  });
});

// =====================================================================
// D6: TELEMETRY SNAPSHOT COMPLETENESS
// =====================================================================

describe("D6: Telemetry snapshot completeness", () => {
  test("snapshot has all required fields after tick", () => {
    tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    const snap = kernelTelemetry.getSnapshot();

    expect(Array.isArray(snap.events)).toBe(true);
    expect(Array.isArray(snap.alignmentEvents)).toBe(true);
    expect(Array.isArray(snap.recentStrategies)).toBe(true);
    expect(Array.isArray(snap.alignment)).toBe(true);
    expect(Array.isArray(snap.alignmentHistory)).toBe(true);
    expect(snap.drift).toBeDefined();
    expect(typeof snap.drift.drifting).toBe("boolean");
    expect(snap.safeMode).toBeDefined();
    expect(typeof snap.safeMode.active).toBe("boolean");
    expect(Array.isArray(snap.recentApprovals)).toBe(true);
    expect(snap.rollbackRegistry).toBeDefined();
    expect(Array.isArray(snap.rollbackRegistry.activeChanges)).toBe(true);
    expect(snap.operatorTrust).toBeDefined();
    expect(typeof snap.operatorTrust.posture).toBe("string");
    expect(typeof snap.operatorTrust.trustScore).toBe("number");
  });

  test("no undefined values in snapshot", () => {
    tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    const snap = kernelTelemetry.getSnapshot();

    const keys = Object.keys(snap) as Array<keyof KernelTelemetrySnapshot>;
    for (const key of keys) {
      expect(snap[key]).not.toBeUndefined();
    }
  });

  test("snapshot accumulates over multiple ticks", () => {
    for (let i = 0; i < 5; i++) {
      tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    }
    const snap = kernelTelemetry.getSnapshot();
    expect(snap.events.length).toBe(5);
    expect(snap.recentStrategies.length).toBe(5);
    expect(snap.alignmentHistory.length).toBe(5);
  });

  test("alignment history points have correct shape", () => {
    tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    const snap = kernelTelemetry.getSnapshot();

    for (const pt of snap.alignmentHistory) {
      expect(typeof pt.timestamp).toBe("number");
      expect(typeof pt.strategy).toBe("string");
      expect(typeof pt.alignment).toBe("number");
      expect(typeof pt.confidence).toBe("number");
    }
  });
});

// =====================================================================
// D5/D7: CROSS-MODULE COMPOSITION + INVARIANT ENFORCEMENT
// =====================================================================

describe("D5/D7: Cross-module composition", () => {
  test("change classifier feeds into auto-approval gate", () => {
    const input: ChangeImpactInput = { surfaces: ["governance_policy"], depth: "deep", reversible: false };
    const classification = classifyChangeImpact(input);
    expect(classification.impact).toBe("high");

    const invariants = detectInvariantTouchBySurface(input.surfaces);
    expect(invariants.touchesInvariants).toBe(true);
    expect(invariants.invariantsTouched).toContain("governance_policy");
  });

  test("classifyChange returns combined result", () => {
    const result = classifyChange({ surfaces: ["telemetry"], depth: "shallow", reversible: true });
    expect(result.impact).toBeDefined();
    expect(result.invariants).toBeDefined();
    expect(result.invariants.touchesInvariants).toBe(false);
  });

  test("operator trust gates compose with auto-approval", () => {
    tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });

    bindOperator(spencerProfile);
    for (let t = 1; t <= 500; t++) updateOperatorTrust(mkObs(t, {}, true));

    const trustState = getOperatorTrustState();
    expect(trustState.trustScore).toBeGreaterThanOrEqual(85);
    expect(trustState.calibrated).toBe(true);

    const result = updateOperatorTrust(mkObs(501, { highRiskRequest: true }, true));
    expect(result.allowHighRiskActions).toBe(true);
  });

  test("constitutional freeze overrides operator trust", () => {
    bindOperator(spencerProfile);
    for (let t = 1; t <= 500; t++) updateOperatorTrust(mkObs(t, {}, true));

    enableConstitutionalFreeze("governance_lockdown");
    const result = updateOperatorTrust(mkObs(501, { highRiskRequest: true }, true));
    expect(result.allowHighRiskActions).toBe(false);
    disableConstitutionalFreeze();
  });

  test("regulation loop produces valid drift metrics", () => {
    for (let i = 0; i < 10; i++) tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    const history = kernelTelemetry.getAlignmentHistory();
    const metrics = computeDriftMetrics(history, DEFAULT_REGULATION_CONFIG.targetAlignment);
    expect(typeof metrics.magnitude).toBe("number");
    expect(typeof metrics.slope).toBe("number");
    expect(typeof metrics.acceleration).toBe("number");
  });

  test("rollback registry lifecycle", () => {
    const record = registerChange({
      id: "test-change-1",
      description: "test config change",
      evaluationWindow: 3,
      baselineAlignment: 90,
      surfaces: ["non_critical_config"],
      impact: "low",
      rollbackPayload: { key: "value" },
    });
    expect(record.status).toBe("active");
    expect(getActiveChanges()).toHaveLength(1);

    processRollbacks(92);
    processRollbacks(92);
    processRollbacks(92);

    const snap = getRollbackRegistrySnapshot();
    expect(snap.activeChanges.length + snap.acceptedCount + snap.rolledBackCount).toBeGreaterThan(0);
  });

  test("no-silent-drift invariant always denies", () => {
    const mutations = [
      "change_trust_threshold",
      "modify_high_risk_list",
      "alter_posture_config",
      "disable_operator_checks",
    ];
    for (const m of mutations) {
      const result = enforceNoSilentDrift(m);
      expect(result.allowed).toBe(false);
      expect(result.reason).toContain("no-silent-drift");
    }
  });

  test("HIGH_RISK_ACTIONS is frozen and contains expected items", () => {
    expect(HIGH_RISK_ACTIONS.length).toBeGreaterThan(0);
    expect(HIGH_RISK_ACTIONS).toContain("edit_governance_policy");
    expect(HIGH_RISK_ACTIONS).toContain("modify_invariants");
    expect(HIGH_RISK_ACTIONS).toContain("operator_handoff");
    expect(() => (HIGH_RISK_ACTIONS as any).push("hack")).toThrow();
  });

  test("defaults are frozen", () => {
    expect(() => (DEFAULT_KERNEL_CONFIG as any).strategySensitivity = 999).toThrow();
    expect(() => (DEFAULT_ALIGNMENT_CONFIG as any).sovereigntyWeight = 999).toThrow();
    expect(() => (DEFAULT_REGULATION_CONFIG as any).targetAlignment = 999).toThrow();
    expect(() => (DEFAULT_ROLLBACK_CONFIG as any).degradationThreshold = 999).toThrow();
    expect(() => (DEFAULT_APPROVAL_GATE_CONFIG as any).alignmentThreshold = 999).toThrow();
    expect(() => (DEFAULT_OPERATOR_TRUST_CONFIG as any).riseRate = 999).toThrow();
    expect(() => (DEFAULT_POSTURE_CONFIG as any).trustedCanonicalThreshold = 999).toThrow();
  });
});

// =====================================================================
// D9: EDGE CASES + ADVERSARIAL
// =====================================================================

describe("D9: Edge cases and adversarial inputs", () => {
  test("tickKernel with empty context (no beings)", () => {
    const ctx = mkContext({ beings: [] });
    const result = tickKernel(ctx, { ...DEFAULT_KERNEL_CONFIG });
    expect(result.strategy).toBeDefined();
    expect(result.strategy.alignment).toBeGreaterThanOrEqual(0);
  });

  test("tickKernel with failed constitution", () => {
    const ctx = mkContext({
      constitutionReport: { allPassed: false, failedCount: 3, checks: [
        { name: "valid-posture" as const, passed: false, detail: "fail" },
      ] },
    });
    const result = tickKernel(ctx, { ...DEFAULT_KERNEL_CONFIG });
    expect(result.strategy.alignment).toBeDefined();
  });

  test("tickKernel with extreme node counts", () => {
    const ctx = mkContext({ nodeCount: 10000, quarantinedCount: 5000, totalErrors: 9999 });
    const result = tickKernel(ctx, { ...DEFAULT_KERNEL_CONFIG });
    expect(result.strategy).toBeDefined();
  });

  test("operator trust with rapid bind/unbind cycles", () => {
    for (let i = 0; i < 10; i++) {
      bindOperator(spencerProfile);
      updateOperatorTrust(mkObs(i, {}, true));
      unbindOperator();
    }
    expect(getOperatorTrustState().boundOperator).toBeNull();
    expect(getOperatorTrustState().trustScore).toBe(0);
  });

  test("operator trust with contradictory signals", () => {
    bindOperator(spencerProfile);
    const result = updateOperatorTrust(mkObs(1, {
      credentialsValid: true,
      deviceKnown: true,
      deviceSuspicious: true,
      behaviorMatchScore: 100,
      continuityMatchScore: 0,
      highRiskRequest: true,
    }));
    expect(typeof result.state.trustScore).toBe("number");
    expect(result.state.trustScore).toBeGreaterThanOrEqual(0);
    expect(result.state.trustScore).toBeLessThanOrEqual(100);
  });

  test("operator trust with all zero signals", () => {
    bindOperator(spencerProfile);
    const result = updateOperatorTrust(mkObs(1, {
      credentialsValid: false,
      deviceKnown: false,
      deviceSuspicious: false,
      behaviorMatchScore: 0,
      continuityMatchScore: 0,
      highRiskRequest: false,
    }));
    expect(result.state.trustScore).toBe(0);
    expect(result.allowHighRiskActions).toBe(false);
  });

  test("operator trust with all perfect signals (no canonical)", () => {
    bindOperator(spencerProfile);
    for (let t = 1; t <= 200; t++) {
      updateOperatorTrust(mkObs(t, {
        credentialsValid: true,
        deviceKnown: true,
        deviceSuspicious: false,
        behaviorMatchScore: 100,
        continuityMatchScore: 100,
        highRiskRequest: false,
      }));
    }
    const state = getOperatorTrustState();
    expect(state.calibrated).toBe(false);
  });

  test("change classifier with empty surfaces", () => {
    const result = classifyChangeImpact({ surfaces: [], depth: "shallow", reversible: true });
    expect(result.impact).toBe("low");
  });

  test("change classifier with all surfaces", () => {
    const allSurfaces = [
      "telemetry", "logging", "ui_presentation", "non_critical_config",
      "performance_tuning", "alignment_tuning", "governance_policy",
      "identity", "continuity", "posture", "node_authority",
      "persistence", "network_topology",
    ] as const;
    const result = classifyChangeImpact({
      surfaces: [...allSurfaces],
      depth: "deep",
      reversible: false,
    });
    expect(result.impact).toBe("high");
  });

  test("continuity seal with empty profile", () => {
    const seal = computeContinuitySeal(null, DEFAULT_OPERATOR_TRUST_CONFIG);
    expect(verifyContinuitySeal(seal, null, DEFAULT_OPERATOR_TRUST_CONFIG)).toBe(true);
    expect(verifyContinuitySeal(seal, spencerProfile, DEFAULT_OPERATOR_TRUST_CONFIG)).toBe(false);
  });

  test("red-team: 200 ticks of normal then 100 of attack", () => {
    const bound = {
      boundOperator: spencerProfile,
      trustScore: 0,
      axes: { credentials: 0, deviceGraph: 0, behaviorProfile: 0, continuity: 0 },
      calibrated: false,
      lastUpdateTick: 0,
    } as const;

    const normalSteps = Array.from({ length: 200 }, (_, i) => ({
      observation: mkObs(i + 1, {}, true),
      description: `normal ${i + 1}`,
    }));

    const attackSteps = Array.from({ length: 100 }, (_, i) => ({
      observation: mkObs(201 + i, {
        credentialsValid: true,
        deviceKnown: true,
        deviceSuspicious: true,
        behaviorMatchScore: 10,
        continuityMatchScore: 5,
        highRiskRequest: true,
      }),
      description: `attack ${i + 1}`,
    }));

    const result = runRedTeamScenario(
      { ...bound, axes: { ...bound.axes } },
      DEFAULT_OPERATOR_TRUST_CONFIG,
      DEFAULT_POSTURE_CONFIG,
      {
        id: "slow_mimic",
        description: "Normal trust buildup then device-based attack",
        steps: [...normalSteps, ...attackSteps],
      },
    );

    expect(result.finalPosture).not.toBe("trusted_canonical");
    expect(result.suspiciousCount).toBeGreaterThan(0);
  });

  test("attunement double-start is safe", () => {
    startAttunement();
    startAttunement();
    expect(getAttunementState()!.completed).toBe(false);
    expect(getAttunementState()!.currentStepIndex).toBe(0);
  });

  test("freeze toggle rapid cycling", () => {
    for (let i = 0; i < 20; i++) {
      enableConstitutionalFreeze(`cycle-${i}`);
      expect(getConstitutionalFreezeState().frozen).toBe(true);
      disableConstitutionalFreeze();
      expect(getConstitutionalFreezeState().frozen).toBe(false);
    }
  });

  test("self-audit with matching config", () => {
    const result = runSelfAudit(null, DEFAULT_OPERATOR_TRUST_CONFIG);
    expect(result.clean).toBe(true);
  });

  test("self-audit with bound operator (profile mismatch)", () => {
    bindOperator(spencerProfile);
    const result = runSelfAudit(null, DEFAULT_OPERATOR_TRUST_CONFIG);
    expect(result.profileIntegrity).toBe(false);
  });

  test("self-audit with correct profile", () => {
    bindOperator(spencerProfile);
    const result = runSelfAudit(spencerProfile, DEFAULT_OPERATOR_TRUST_CONFIG);
    expect(result.profileIntegrity).toBe(true);
    expect(result.clean).toBe(true);
  });

  test("introspection outputs are strings", () => {
    expect(typeof introspectPosture()).toBe("string");
    expect(introspectPosture()).toContain("Posture");
  });

  test("comfort layer view covers all postures", () => {
    const view = buildComfortLayerView();
    expect(view.posture).toBe("unbound");
    expect(view.narrative).toBeTruthy();
    expect(typeof view.comfortPosture).toBe("string");
  });

  test("future-you sanity check with clean config", () => {
    const result = runFutureYouSanityCheck(
      100,
      { invariantsVersion: "v1", description: "initial", keyInvariants: [] },
      "v1", "v1",
      DEFAULT_OPERATOR_TRUST_CONFIG,
      DEFAULT_OPERATOR_TRUST_CONFIG,
    );
    expect(result.invariantsMatch).toBe(true);
    expect(result.configMatch).toBe(true);
    expect(result.driftSignals).toHaveLength(0);
  });

  test("future-you sanity check detects drift", () => {
    const result = runFutureYouSanityCheck(
      100,
      { invariantsVersion: "v1", description: "initial", keyInvariants: [] },
      "v1", "v2",
      DEFAULT_OPERATOR_TRUST_CONFIG,
      { ...DEFAULT_OPERATOR_TRUST_CONFIG, riseRate: 99 },
    );
    expect(result.invariantsMatch).toBe(false);
    expect(result.configMatch).toBe(false);
    expect(result.driftSignals.length).toBeGreaterThan(0);
  });

  test("weekly trust narrative with no data returns correct text", () => {
    const n = buildWeeklyTrustNarrative(0, 100);
    expect(n.text).toContain("No operator activity");
    expect(n.avgTrust).toBe(0);
  });

  test("relationship timeline respects order", () => {
    addRelationshipEvent({ tick: 50, kind: "milestone", title: "B", description: "" });
    addRelationshipEvent({ tick: 10, kind: "ritual", title: "A", description: "" });
    addRelationshipEvent({ tick: 100, kind: "anomaly", title: "C", description: "" });
    const tl = getRelationshipTimeline();
    expect(tl.events[0].tick).toBe(10);
    expect(tl.events[1].tick).toBe(50);
    expect(tl.events[2].tick).toBe(100);
  });
});

// =====================================================================
// MULTI-TICK PIPELINE SIMULATION
// =====================================================================

describe("Multi-tick pipeline simulation", () => {
  test("50-tick pipeline stability", () => {
    const config = { ...DEFAULT_KERNEL_CONFIG };
    const ctx = mkContext();

    const alignments: number[] = [];
    const postures: string[] = [];

    for (let i = 0; i < 50; i++) {
      const result = tickKernel(ctx, config);
      alignments.push(result.strategy.alignment);
      postures.push(result.operatorTrust.posture);

      expect(result.strategy.alignment).toBeGreaterThanOrEqual(0);
      expect(result.strategy.alignment).toBeLessThanOrEqual(100);
      expect(result.posture.responsiveness).toBeGreaterThanOrEqual(0);
      expect(result.posture.caution).toBeGreaterThanOrEqual(0);
    }

    const snap = kernelTelemetry.getSnapshot();
    expect(snap.events.length).toBe(50);
    expect(snap.alignmentHistory.length).toBe(50);

    const avgAlignment = alignments.reduce((a, b) => a + b, 0) / alignments.length;
    expect(avgAlignment).toBeGreaterThan(0);
  });

  test("50-tick pipeline with operator trust buildup", () => {
    bindOperator(spencerProfile);
    const config = { ...DEFAULT_KERNEL_CONFIG };
    const ctx = mkContext();

    for (let i = 1; i <= 50; i++) {
      updateOperatorTrust(mkObs(i, {}, true));
      tickKernel(ctx, config);
    }

    const trustState = getOperatorTrustState();
    expect(trustState.trustScore).toBeGreaterThan(0);

    const snap = kernelTelemetry.getSnapshot();
    expect(snap.operatorTrust.posture).not.toBe("hostile_or_unknown");
  });
});
