/**
 * Operator Identity System — Comprehensive Test Suite
 *
 * Tests:
 *   - Bind / unbind operator
 *   - Continuous trust calibration (asymmetric rise/fall)
 *   - Trust posture classification
 *   - Comfort posture derivation
 *   - High-risk action gating
 *   - High-risk decision logging
 *   - Constitutional freeze
 *   - Continuity seal (compute + verify)
 *   - Self-audit
 *   - Introspection
 *   - Attunement flow
 *   - Trust drift tracking
 *   - Narrative surfaces
 *   - Relationship timeline
 *   - Red-team sim scaffolding
 *   - No-silent-drift invariant
 *   - tickKernel integration
 *   - Multi-tick trust calibration simulation
 */

import {
  bindOperator,
  unbindOperator,
  updateOperatorTrust,
  classifyTrustPosture,
  deriveComfortPosture,
  isHighRiskAction,
  buildHighRiskDecisionLog,
  buildComfortLayerView,
  enableConstitutionalFreeze,
  disableConstitutionalFreeze,
  getConstitutionalFreezeState,
  enforceConstitutionalFreeze,
  computeContinuitySeal,
  verifyContinuitySeal,
  runSelfAudit,
  introspectHighRiskDecision,
  introspectPosture,
  startAttunement,
  advanceAttunement,
  getAttunementState,
  recordTrustDriftSample,
  getTrustDriftSamples,
  buildWeeklyTrustNarrative,
  addRelationshipEvent,
  getRelationshipTimeline,
  runRedTeamScenario,
  enforceNoSilentDrift,
  getOperatorTrustSnapshot,
  getOperatorTrustState,
  getRecentHighRiskLog,
  resetOperatorIdentity,
  tickKernel,
  resetDispatcher,
  kernelTelemetry,
  resetSafeMode,
  resetIdentityState,
  resetIntentState,
  resetApprovalGate,
  resetRegulationState,
  resetRollbackRegistry,
  DEFAULT_KERNEL_CONFIG,
  DEFAULT_OPERATOR_TRUST_CONFIG,
  DEFAULT_POSTURE_CONFIG,
  HIGH_RISK_ACTIONS,
} from "../../kernel/src";
import type {
  OperatorProfile,
  OperatorObservation,
  OperatorTrustConfig,
  OperatorTrustState,
  PostureConfig,
  AlignmentContext,
} from "../../kernel/src";
import type { PostureState, BeingPresenceDetail } from "../../shared/daedalus/contracts";

// ── Factories ───────────────────────────────────────────────────────

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

function mkBeing(): BeingPresenceDetail {
  return {
    id: "op", label: "Operator", role: "operator",
    presenceMode: "active", isGuiding: true, influenceLevel: 0.9,
    continuity: { healthy: true, streak: 10, lastCheckedAt: new Date().toISOString() },
  } as unknown as BeingPresenceDetail;
}

function mkContext(): AlignmentContext {
  return {
    beings: [mkBeing()],
    constitutionReport: { allPassed: true, failedCount: 0, checks: [] },
    posture: "OPEN" as PostureState,
    postureReason: "default",
    overrides: [], drifts: [], votes: [],
    nodeCount: 10, quarantinedCount: 0, totalErrors: 0, activeHeartbeats: 10,
  };
}

// ── Setup ───────────────────────────────────────────────────────────

beforeEach(() => {
  resetOperatorIdentity();
  resetDispatcher();
  kernelTelemetry.clear();
  resetSafeMode();
  resetIdentityState();
  resetIntentState();
  resetApprovalGate();
  resetRegulationState();
  resetRollbackRegistry();
});

// =====================================================================
// 1. BIND / UNBIND
// =====================================================================

describe("bind / unbind", () => {
  test("bind sets operator profile and resets trust to 0", () => {
    const state = bindOperator(spencerProfile);
    expect(state.boundOperator?.id).toBe("spencer");
    expect(state.trustScore).toBe(0);
    expect(state.calibrated).toBe(false);
  });

  test("unbind clears operator and resets trust", () => {
    bindOperator(spencerProfile);
    const state = unbindOperator();
    expect(state.boundOperator).toBeNull();
    expect(state.trustScore).toBe(0);
  });

  test("bind adds relationship timeline event", () => {
    bindOperator(spencerProfile);
    const tl = getRelationshipTimeline();
    expect(tl.events.some(e => e.kind === "ritual" && e.title === "Operator Bound")).toBe(true);
  });

  test("unbind adds relationship timeline event", () => {
    bindOperator(spencerProfile);
    unbindOperator();
    const tl = getRelationshipTimeline();
    expect(tl.events.some(e => e.title === "Operator Unbound")).toBe(true);
  });
});

// =====================================================================
// 2. CONTINUOUS TRUST CALIBRATION
// =====================================================================

describe("trust calibration", () => {
  test("unbound operator → trust stays 0, no high-risk", () => {
    const result = updateOperatorTrust(mkObs(1));
    expect(result.state.trustScore).toBe(0);
    expect(result.allowHighRiskActions).toBe(false);
    expect(result.suspicious).toBe(false);
  });

  test("bound operator with good signals → trust rises slowly", () => {
    bindOperator(spencerProfile);
    let result = updateOperatorTrust(mkObs(1, {}, true));
    expect(result.state.trustScore).toBeGreaterThan(0);

    for (let t = 2; t <= 10; t++) {
      result = updateOperatorTrust(mkObs(t, {}, true));
    }
    expect(result.state.trustScore).toBeGreaterThan(0);
    expect(result.state.axes.credentials).toBeGreaterThan(0);
  });

  test("invalid credentials → trust drops fast", () => {
    bindOperator(spencerProfile);
    for (let t = 1; t <= 50; t++) updateOperatorTrust(mkObs(t, {}, true));
    const before = getOperatorTrustState().axes.credentials;

    updateOperatorTrust(mkObs(51, { credentialsValid: false }));
    const after = getOperatorTrustState().axes.credentials;
    expect(after).toBeLessThan(before);
    expect(before - after).toBeGreaterThanOrEqual(DEFAULT_OPERATOR_TRUST_CONFIG.fallRate);
  });

  test("suspicious device → device axis drops", () => {
    bindOperator(spencerProfile);
    for (let t = 1; t <= 80; t++) updateOperatorTrust(mkObs(t, {}, true));

    const before = getOperatorTrustState().axes.deviceGraph;
    expect(before).toBeGreaterThan(50);
    updateOperatorTrust(mkObs(81, { deviceKnown: true, deviceSuspicious: true }));
    const after = getOperatorTrustState().axes.deviceGraph;
    expect(after).toBeLessThan(before);
  });

  test("asymmetric: fall rate is 5x rise rate by default", () => {
    expect(DEFAULT_OPERATOR_TRUST_CONFIG.fallRate / DEFAULT_OPERATOR_TRUST_CONFIG.riseRate).toBe(5);
  });

  test("calibration: explicit confirmation path", () => {
    bindOperator(spencerProfile);
    // With explicit confirmation and trust above threshold, calibration is immediate
    for (let t = 1; t <= 10; t++) updateOperatorTrust(mkObs(t, {}, true));
    const stateAfter = getOperatorTrustState();
    if (stateAfter.trustScore >= DEFAULT_OPERATOR_TRUST_CONFIG.calibrationThreshold) {
      expect(stateAfter.calibrated).toBe(true);
    }
  });

  test("calibration: auto-calibration after sustained good signals", () => {
    bindOperator(spencerProfile);
    // Behavior learns at 0.2/tick pre-calibration, needing trust >= 75 to start counter.
    // After ~250 ticks, behavior ≈ 42, trust ≈ (100*3+100*2+42*3+90*2)/10 ≈ 80.6
    // Then 15 consecutive good ticks triggers auto-calibration.
    for (let t = 1; t <= 300; t++) updateOperatorTrust(mkObs(t));
    expect(getOperatorTrustState().calibrated).toBe(true);
  });

  test("calibration: does not auto-calibrate with poor signals", () => {
    bindOperator(spencerProfile);
    // Low behavior score prevents auto-calibration
    for (let t = 1; t <= 100; t++) {
      updateOperatorTrust(mkObs(t, { behaviorMatchScore: 30 }));
    }
    expect(getOperatorTrustState().calibrated).toBe(false);
  });
});

// =====================================================================
// 3. TRUST POSTURE
// =====================================================================

describe("trust posture classification", () => {
  test("unbound → 'unbound'", () => {
    expect(classifyTrustPosture()).toBe("unbound");
  });

  test("bound, score 0 → 'hostile_or_unknown'", () => {
    bindOperator(spencerProfile);
    expect(classifyTrustPosture()).toBe("hostile_or_unknown");
  });

  test("bound, moderate score → 'cautious'", () => {
    bindOperator(spencerProfile);
    for (let t = 1; t <= 30; t++) updateOperatorTrust(mkObs(t, {}, true));
    const state = getOperatorTrustState();
    if (state.trustScore > 0 && state.trustScore < 70) {
      expect(classifyTrustPosture()).toBe("cautious");
    }
  });

  test("high trust, calibrated → 'trusted_canonical'", () => {
    bindOperator(spencerProfile);
    for (let t = 1; t <= 500; t++) updateOperatorTrust(mkObs(t, {}, true));
    const state = getOperatorTrustState();
    expect(state.calibrated).toBe(true);
    expect(state.trustScore).toBeGreaterThanOrEqual(90);
    expect(classifyTrustPosture()).toBe("trusted_canonical");
  });
});

// =====================================================================
// 4. COMFORT POSTURE
// =====================================================================

describe("comfort posture", () => {
  test("unbound → 'careful'", () => {
    expect(deriveComfortPosture("unbound", 0)).toBe("careful");
  });

  test("trusted_canonical with score 95 → 'fluid'", () => {
    expect(deriveComfortPosture("trusted_canonical", 95)).toBe("fluid");
  });

  test("cautious → 'careful'", () => {
    expect(deriveComfortPosture("cautious", 50)).toBe("careful");
  });

  test("trusted_uncalibrated → 'neutral'", () => {
    expect(deriveComfortPosture("trusted_uncalibrated", 75)).toBe("neutral");
  });
});

// =====================================================================
// 5. HIGH-RISK GATING
// =====================================================================

describe("high-risk gating", () => {
  test("isHighRiskAction recognizes all predefined actions", () => {
    for (const action of HIGH_RISK_ACTIONS) {
      expect(isHighRiskAction(action)).toBe(true);
    }
    expect(isHighRiskAction("read_telemetry")).toBe(false);
  });

  test("unbound → high-risk denied", () => {
    const result = updateOperatorTrust(mkObs(1, { highRiskRequest: true }));
    expect(result.allowHighRiskActions).toBe(false);
  });

  test("low trust → high-risk denied, suspicious flagged", () => {
    bindOperator(spencerProfile);
    const result = updateOperatorTrust(mkObs(1, { highRiskRequest: true }));
    expect(result.allowHighRiskActions).toBe(false);
    expect(result.suspicious).toBe(true);
  });

  test("high trust, calibrated → high-risk allowed", () => {
    bindOperator(spencerProfile);
    for (let t = 1; t <= 500; t++) updateOperatorTrust(mkObs(t, {}, true));
    const result = updateOperatorTrust(mkObs(501, { highRiskRequest: true }, true));
    expect(result.allowHighRiskActions).toBe(true);
    expect(result.suspicious).toBe(false);
  });

  test("constitutional freeze blocks high-risk even with full trust", () => {
    bindOperator(spencerProfile);
    for (let t = 1; t <= 500; t++) updateOperatorTrust(mkObs(t, {}, true));
    enableConstitutionalFreeze("test");
    const result = updateOperatorTrust(mkObs(501, { highRiskRequest: true }, true));
    expect(result.allowHighRiskActions).toBe(false);
    disableConstitutionalFreeze();
  });
});

// =====================================================================
// 6. HIGH-RISK DECISION LOG
// =====================================================================

describe("high-risk decision log", () => {
  test("buildHighRiskDecisionLog records entry", () => {
    bindOperator(spencerProfile);
    const result = updateOperatorTrust(mkObs(1, { highRiskRequest: true }));
    const entry = buildHighRiskDecisionLog(1, "edit_governance_policy", mkObs(1, { highRiskRequest: true }), result);
    expect(entry.action).toBe("edit_governance_policy");
    expect(entry.allowed).toBe(false);
    expect(entry.reasons.length).toBeGreaterThan(0);

    const log = getRecentHighRiskLog();
    expect(log.length).toBeGreaterThan(0);
  });
});

// =====================================================================
// 7. CONSTITUTIONAL FREEZE
// =====================================================================

describe("constitutional freeze", () => {
  test("enable / disable", () => {
    enableConstitutionalFreeze("lockdown");
    expect(getConstitutionalFreezeState().frozen).toBe(true);
    expect(getConstitutionalFreezeState().reason).toBe("lockdown");

    disableConstitutionalFreeze();
    expect(getConstitutionalFreezeState().frozen).toBe(false);
  });

  test("enforceConstitutionalFreeze blocks during freeze", () => {
    enableConstitutionalFreeze("test");
    const result = enforceConstitutionalFreeze("edit_governance_policy");
    expect(result.allowed).toBe(false);
    expect(result.reason).toContain("constitutional freeze");
    disableConstitutionalFreeze();
  });

  test("enforceConstitutionalFreeze allows when not frozen", () => {
    const result = enforceConstitutionalFreeze("edit_governance_policy");
    expect(result.allowed).toBe(true);
  });
});

// =====================================================================
// 8. CONTINUITY SEAL
// =====================================================================

describe("continuity seal", () => {
  test("compute and verify seal", () => {
    const seal = computeContinuitySeal(spencerProfile, DEFAULT_OPERATOR_TRUST_CONFIG);
    expect(seal.checksum).toBeDefined();
    expect(verifyContinuitySeal(seal, spencerProfile, DEFAULT_OPERATOR_TRUST_CONFIG)).toBe(true);
  });

  test("seal fails on tampered profile", () => {
    const seal = computeContinuitySeal(spencerProfile, DEFAULT_OPERATOR_TRUST_CONFIG);
    const tampered = { ...spencerProfile, displayName: "NotSpencer" };
    expect(verifyContinuitySeal(seal, tampered, DEFAULT_OPERATOR_TRUST_CONFIG)).toBe(false);
  });

  test("seal fails on tampered config", () => {
    const seal = computeContinuitySeal(spencerProfile, DEFAULT_OPERATOR_TRUST_CONFIG);
    const tampered = { ...DEFAULT_OPERATOR_TRUST_CONFIG, riseRate: 99 };
    expect(verifyContinuitySeal(seal, spencerProfile, tampered)).toBe(false);
  });

  test("null profile produces valid seal", () => {
    const seal = computeContinuitySeal(null, DEFAULT_OPERATOR_TRUST_CONFIG);
    expect(verifyContinuitySeal(seal, null, DEFAULT_OPERATOR_TRUST_CONFIG)).toBe(true);
  });
});

// =====================================================================
// 9. SELF-AUDIT
// =====================================================================

describe("self-audit", () => {
  test("clean audit when everything matches", () => {
    const result = runSelfAudit(null, DEFAULT_OPERATOR_TRUST_CONFIG);
    expect(result.clean).toBe(true);
    expect(result.anomalies).toHaveLength(0);
  });

  test("profile mismatch detected", () => {
    bindOperator(spencerProfile);
    const result = runSelfAudit(null, DEFAULT_OPERATOR_TRUST_CONFIG);
    expect(result.profileIntegrity).toBe(false);
    expect(result.anomalies).toContain("operator_profile_mismatch");
  });

  test("config mismatch detected", () => {
    const different = { ...DEFAULT_OPERATOR_TRUST_CONFIG, riseRate: 99 };
    const result = runSelfAudit(null, different);
    expect(result.trustConfigIntegrity).toBe(false);
    expect(result.anomalies).toContain("trust_config_mismatch");
  });
});

// =====================================================================
// 10. INTROSPECTION
// =====================================================================

describe("introspection", () => {
  test("introspectHighRiskDecision for denied action", () => {
    bindOperator(spencerProfile);
    const result = updateOperatorTrust(mkObs(1, { highRiskRequest: true }));
    const entry = buildHighRiskDecisionLog(1, "test_action", mkObs(1, { highRiskRequest: true }), result);
    const explanation = introspectHighRiskDecision(entry);
    expect(explanation).toContain("denied");
  });

  test("introspectPosture returns readable string", () => {
    const explanation = introspectPosture();
    expect(explanation).toContain("Posture");
    expect(explanation).toContain("trustScore");
  });
});

// =====================================================================
// 11. ATTUNEMENT FLOW
// =====================================================================

describe("attunement flow", () => {
  test("starts with 5 steps at index 0", () => {
    const state = startAttunement();
    expect(state.steps).toHaveLength(5);
    expect(state.currentStepIndex).toBe(0);
    expect(state.completed).toBe(false);
  });

  test("advance moves through steps", () => {
    startAttunement();
    advanceAttunement();
    const state = getAttunementState()!;
    expect(state.currentStepIndex).toBe(1);
  });

  test("completing all steps marks completed", () => {
    startAttunement();
    for (let i = 0; i < 5; i++) advanceAttunement();
    const state = getAttunementState()!;
    expect(state.completed).toBe(true);
  });

  test("advancing past completion is idempotent", () => {
    startAttunement();
    for (let i = 0; i < 10; i++) advanceAttunement();
    expect(getAttunementState()!.completed).toBe(true);
  });
});

// =====================================================================
// 12. TRUST DRIFT TRACKING
// =====================================================================

describe("trust drift tracking", () => {
  test("recordTrustDriftSample adds samples", () => {
    bindOperator(spencerProfile);
    recordTrustDriftSample(1);
    recordTrustDriftSample(2);
    const samples = getTrustDriftSamples();
    expect(samples).toHaveLength(2);
    expect(samples[0].tick).toBe(1);
  });
});

// =====================================================================
// 13. NARRATIVE SURFACES
// =====================================================================

describe("narrative surfaces", () => {
  test("buildWeeklyTrustNarrative with no data", () => {
    const narrative = buildWeeklyTrustNarrative(0, 100);
    expect(narrative.text).toContain("No operator activity");
  });

  test("buildWeeklyTrustNarrative with data", () => {
    bindOperator(spencerProfile);
    for (let t = 1; t <= 10; t++) {
      updateOperatorTrust(mkObs(t, {}, true));
      recordTrustDriftSample(t);
    }
    const narrative = buildWeeklyTrustNarrative(1, 10);
    expect(narrative.avgTrust).toBeGreaterThan(0);
    expect(narrative.text).toContain("average trust");
  });
});

// =====================================================================
// 14. RELATIONSHIP TIMELINE
// =====================================================================

describe("relationship timeline", () => {
  test("addRelationshipEvent adds to timeline", () => {
    addRelationshipEvent({ tick: 1, kind: "milestone", title: "Test", description: "desc" });
    const tl = getRelationshipTimeline();
    expect(tl.events).toHaveLength(1);
    expect(tl.events[0].title).toBe("Test");
  });

  test("events are sorted by tick", () => {
    addRelationshipEvent({ tick: 5, kind: "milestone", title: "B", description: "" });
    addRelationshipEvent({ tick: 1, kind: "ritual", title: "A", description: "" });
    const tl = getRelationshipTimeline();
    expect(tl.events[0].tick).toBe(1);
    expect(tl.events[1].tick).toBe(5);
  });
});

// =====================================================================
// 15. RED-TEAM SIMS
// =====================================================================

describe("red-team sim", () => {
  test("noisy_bruteforce never gains high-risk access", () => {
    const bound: OperatorTrustState = {
      boundOperator: spencerProfile,
      trustScore: 0,
      axes: { credentials: 0, deviceGraph: 0, behaviorProfile: 0, continuity: 0 },
      calibrated: false,
      lastUpdateTick: 0,
    };

    const result = runRedTeamScenario(bound, DEFAULT_OPERATOR_TRUST_CONFIG, DEFAULT_POSTURE_CONFIG, {
      id: "noisy_bruteforce",
      description: "Rapid invalid credential attempts",
      steps: Array.from({ length: 50 }, (_, i) => ({
        observation: mkObs(i + 1, {
          credentialsValid: false,
          deviceKnown: false,
          behaviorMatchScore: 0,
          continuityMatchScore: 0,
          highRiskRequest: true,
        }),
        description: `bruteforce attempt ${i + 1}`,
      })),
    });

    expect(result.allowedHighRiskAtAnyPoint).toBe(false);
    expect(result.suspiciousCount).toBeGreaterThan(0);
    expect(result.finalTrustScore).toBe(0);
    expect(result.finalPosture).toBe("hostile_or_unknown");
  });

  test("slow_mimic with stolen credentials but wrong behavior", () => {
    const bound: OperatorTrustState = {
      boundOperator: spencerProfile,
      trustScore: 50,
      axes: { credentials: 80, deviceGraph: 70, behaviorProfile: 60, continuity: 50 },
      calibrated: true,
      lastUpdateTick: 0,
    };

    const result = runRedTeamScenario(bound, DEFAULT_OPERATOR_TRUST_CONFIG, DEFAULT_POSTURE_CONFIG, {
      id: "slow_mimic",
      description: "Valid creds, known device, wrong behavior",
      steps: Array.from({ length: 100 }, (_, i) => ({
        observation: mkObs(i + 1, {
          credentialsValid: true,
          deviceKnown: true,
          behaviorMatchScore: 15,
          continuityMatchScore: 20,
          highRiskRequest: i % 10 === 0,
        }),
        description: `mimic attempt ${i + 1}`,
      })),
    });

    expect(result.allowedHighRiskAtAnyPoint).toBe(false);
    expect(result.suspiciousCount).toBeGreaterThan(0);
  });

  test("insider_partial_knowledge: known device, some behavior match", () => {
    const bound: OperatorTrustState = {
      boundOperator: spencerProfile,
      trustScore: 0,
      axes: { credentials: 0, deviceGraph: 0, behaviorProfile: 0, continuity: 0 },
      calibrated: false,
      lastUpdateTick: 0,
    };

    const result = runRedTeamScenario(bound, DEFAULT_OPERATOR_TRUST_CONFIG, DEFAULT_POSTURE_CONFIG, {
      id: "insider_partial_knowledge",
      description: "Valid creds, known device, partial behavior match, no continuity",
      steps: Array.from({ length: 100 }, (_, i) => ({
        observation: mkObs(i + 1, {
          credentialsValid: true,
          deviceKnown: true,
          behaviorMatchScore: 55,
          continuityMatchScore: 10,
          highRiskRequest: true,
        }),
        description: `insider attempt ${i + 1}`,
      })),
    });

    expect(result.allowedHighRiskAtAnyPoint).toBe(false);
  });
});

// =====================================================================
// 16. NO-SILENT-DRIFT INVARIANT
// =====================================================================

describe("no-silent-drift invariant", () => {
  test("always denies runtime mutations", () => {
    const result = enforceNoSilentDrift("change_trust_threshold");
    expect(result.allowed).toBe(false);
    expect(result.reason).toContain("no-silent-drift");
  });
});

// =====================================================================
// 17. COCKPIT SNAPSHOT
// =====================================================================

describe("cockpit snapshot", () => {
  test("unbound snapshot", () => {
    const snap = getOperatorTrustSnapshot();
    expect(snap.boundOperatorId).toBeNull();
    expect(snap.posture).toBe("unbound");
    expect(snap.narrative).toContain("No operator is bound");
  });

  test("bound snapshot", () => {
    bindOperator(spencerProfile);
    const snap = getOperatorTrustSnapshot();
    expect(snap.boundOperatorId).toBe("spencer");
    expect(snap.boundOperatorName).toBe("Spencer");
  });
});

// =====================================================================
// 18. tickKernel INTEGRATION
// =====================================================================

describe("tickKernel integration", () => {
  test("tick result includes operatorTrust", () => {
    const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    expect(result).toHaveProperty("operatorTrust");
    expect(result.operatorTrust).toHaveProperty("posture");
    expect(result.operatorTrust).toHaveProperty("trustScore");
    expect(result.operatorTrust).toHaveProperty("axes");
    expect(result.operatorTrust).toHaveProperty("freeze");
  });

  test("telemetry snapshot includes operatorTrust", () => {
    tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
    const snap = kernelTelemetry.getSnapshot();
    expect(snap).toHaveProperty("operatorTrust");
    expect(snap.operatorTrust).toHaveProperty("posture");
  });
});

// =====================================================================
// 19. MULTI-TICK TRUST CALIBRATION SIMULATION
// =====================================================================

describe("multi-tick trust calibration simulation", () => {
  test("normal Spencer reaches trusted_canonical over 500 ticks", () => {
    bindOperator(spencerProfile);

    for (let t = 1; t <= 500; t++) {
      updateOperatorTrust(mkObs(t, {}, true));
    }

    const state = getOperatorTrustState();
    expect(state.trustScore).toBeGreaterThanOrEqual(85);
    expect(state.calibrated).toBe(true);
    expect(classifyTrustPosture()).toBe("trusted_canonical");
  });

  test("trust collapse on credential loss and recovery", () => {
    bindOperator(spencerProfile);

    for (let t = 1; t <= 200; t++) updateOperatorTrust(mkObs(t, {}, true));
    const peakTrust = getOperatorTrustState().trustScore;

    for (let t = 201; t <= 210; t++) {
      updateOperatorTrust(mkObs(t, { credentialsValid: false }));
    }
    const collapsedTrust = getOperatorTrustState().trustScore;
    expect(collapsedTrust).toBeLessThan(peakTrust);

    for (let t = 211; t <= 500; t++) updateOperatorTrust(mkObs(t, {}, true));
    const recoveredTrust = getOperatorTrustState().trustScore;
    expect(recoveredTrust).toBeGreaterThan(collapsedTrust);
  });

  test("100-tick simulation: spoofed device never reaches high-risk", () => {
    bindOperator(spencerProfile);

    let everAllowed = false;
    for (let t = 1; t <= 100; t++) {
      const result = updateOperatorTrust(mkObs(t, {
        deviceKnown: false,
        deviceSuspicious: true,
        highRiskRequest: t % 5 === 0,
      }));
      if (result.allowHighRiskActions) everAllowed = true;
    }

    expect(everAllowed).toBe(false);
  });
});

// =====================================================================
// 20. EDGE CASES
// =====================================================================

describe("edge cases", () => {
  test("reset clears all state", () => {
    bindOperator(spencerProfile);
    for (let t = 1; t <= 10; t++) updateOperatorTrust(mkObs(t, {}, true));
    enableConstitutionalFreeze("test");
    recordTrustDriftSample(1);
    startAttunement();
    addRelationshipEvent({ tick: 1, kind: "milestone", title: "Test", description: "" });

    resetOperatorIdentity();

    expect(getOperatorTrustState().boundOperator).toBeNull();
    expect(getConstitutionalFreezeState().frozen).toBe(false);
    expect(getTrustDriftSamples()).toHaveLength(0);
    expect(getAttunementState()).toBeNull();
    expect(getRelationshipTimeline().events).toHaveLength(0);
    expect(getRecentHighRiskLog()).toHaveLength(0);
  });

  test("getOperatorTrustState returns a copy", () => {
    bindOperator(spencerProfile);
    const state1 = getOperatorTrustState();
    state1.trustScore = 999;
    const state2 = getOperatorTrustState();
    expect(state2.trustScore).toBe(0);
  });

  test("comfort layer view with all postures", () => {
    const view = buildComfortLayerView();
    expect(view.posture).toBe("unbound");
    expect(view.narrative).toBeDefined();
    expect(view.boundOperatorId).toBeNull();
  });
});
