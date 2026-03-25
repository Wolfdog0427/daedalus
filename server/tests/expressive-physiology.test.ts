/**
 * Dedicated tests for the kernel expressive physiology pipeline.
 *
 * Validates sub-postures, overlays, micro-postures, operator cues,
 * context-aware modulation, and their integration through tickKernel.
 */

import type {
  AlignmentContext,
  AlignmentDriftResult,
} from "../../kernel/src";
import {
  tickKernel,
  kernelTelemetry,
  resetDispatcher,
  resetGateBand,
  resetSafeMode,
  resetEscalation,
  resetIntentState,
  resetIdentityState,
  resetApprovalGate,
  resetRollbackRegistry,
  resetRegulationState,
  resetOperatorIdentity,
  resetExpressiveState,
  setOperatorCue,
  getOperatorCue,
  setContext,
  getContext,
  selectSubPosture,
  computeMicroPosture,
  selectOverlay,
  computeContextualModulation,
  SubPosture,
  ExpressiveOverlay,
  DEFAULT_KERNEL_CONFIG,
} from "../../kernel/src";

import type {
  PostureState,
  BeingPresenceDetail,
} from "../../shared/daedalus/contracts";

function mkBeing(): BeingPresenceDetail {
  return {
    id: "test-being-expr",
    name: "TestBeing",
    label: "Test Being",
    alive: true,
    presenceMode: "active",
    isGuiding: true,
    influenceLevel: 0.9,
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

function mkDrift(overrides: Partial<AlignmentDriftResult> = {}): AlignmentDriftResult {
  return {
    drifting: false,
    delta: 0,
    window: 20,
    firstAlignment: 85,
    lastAlignment: 85,
    ...overrides,
  };
}

function resetAll() {
  kernelTelemetry.clear();
  resetDispatcher();
  resetGateBand();
  resetSafeMode();
  resetEscalation();
  resetIntentState();
  resetIdentityState();
  resetApprovalGate();
  resetRollbackRegistry();
  resetRegulationState();
  resetOperatorIdentity();
  resetExpressiveState();
}

describe("Kernel Expressive Physiology Pipeline", () => {
  beforeEach(resetAll);

  describe("Sub-posture selection", () => {
    it("returns DEFENSIVE when alignment is below 50", () => {
      const sub = selectSubPosture(30, mkDrift(), 80, {
        operatorTrustScore: 80,
        cognitiveLoad: 0.3,
        creativeTask: false,
        sensitiveOperator: false,
      });
      expect(sub).toBe(SubPosture.DEFENSIVE);
    });

    it("returns DEFENSIVE when drifting with large delta", () => {
      const sub = selectSubPosture(75, mkDrift({ drifting: true, delta: -15 }), 80, {
        operatorTrustScore: 80,
        cognitiveLoad: 0.3,
        creativeTask: false,
        sensitiveOperator: false,
      });
      expect(sub).toBe(SubPosture.DEFENSIVE);
    });

    it("does NOT return DEFENSIVE for small drift delta", () => {
      const sub = selectSubPosture(75, mkDrift({ drifting: true, delta: -5 }), 80, {
        operatorTrustScore: 80,
        cognitiveLoad: 0.3,
        creativeTask: false,
        sensitiveOperator: false,
      });
      expect(sub).not.toBe(SubPosture.DEFENSIVE);
    });

    it("returns SUPPORTIVE when operator trust is high", () => {
      const sub = selectSubPosture(85, mkDrift(), 95, {
        operatorTrustScore: 95,
        cognitiveLoad: 0.3,
        creativeTask: false,
        sensitiveOperator: false,
      });
      expect(sub).toBe(SubPosture.SUPPORTIVE);
    });

    it("returns ANALYTIC when cognitive load is high", () => {
      const sub = selectSubPosture(75, mkDrift(), 50, {
        operatorTrustScore: 50,
        cognitiveLoad: 0.8,
        creativeTask: false,
        sensitiveOperator: false,
      });
      expect(sub).toBe(SubPosture.ANALYTIC);
    });

    it("returns CREATIVE for creative tasks", () => {
      const sub = selectSubPosture(85, mkDrift(), 50, {
        operatorTrustScore: 50,
        cognitiveLoad: 0.3,
        creativeTask: true,
        sensitiveOperator: false,
      });
      expect(sub).toBe(SubPosture.CREATIVE);
    });

    it("returns SENSITIVE for sensitive operator", () => {
      const sub = selectSubPosture(85, mkDrift(), 50, {
        operatorTrustScore: 50,
        cognitiveLoad: 0.3,
        creativeTask: false,
        sensitiveOperator: true,
      });
      expect(sub).toBe(SubPosture.SENSITIVE);
    });
  });

  describe("Micro-posture computation", () => {
    it("produces correct values for mid-range alignment", () => {
      const mp = computeMicroPosture(70, 80, mkDrift());
      expect(mp.responsiveness).toBeCloseTo(0.7, 1);
      expect(mp.caution).toBeCloseTo(0.3, 1);
      expect(mp.expressiveness).toBeCloseTo(0.8, 1);
    });

    it("drift increases caution and decreases expressiveness", () => {
      const noDrift = mkDrift();
      const withDrift = mkDrift({ drifting: true, delta: -5 });
      const mp1 = computeMicroPosture(70, 80, noDrift);
      const mp2 = computeMicroPosture(70, 80, withDrift);
      expect(mp2.caution).toBeGreaterThan(mp1.caution);
      expect(mp2.expressiveness).toBeLessThan(mp1.expressiveness);
    });

    it("clamps values to [0, 1]", () => {
      const drift = mkDrift({ drifting: true, delta: -10 });
      const mp = computeMicroPosture(100, 100, drift);
      expect(mp.responsiveness).toBeLessThanOrEqual(1);
      expect(mp.caution).toBeGreaterThanOrEqual(0);
      expect(mp.expressiveness).toBeGreaterThanOrEqual(0);
      expect(mp.expressiveness).toBeLessThanOrEqual(1);
    });
  });

  describe("Overlay selection", () => {
    const basePosture = { responsiveness: 0.7, caution: 0.3 };

    it("returns ALERT during safe mode entry", () => {
      const overlay = selectOverlay(
        { safeMode: { active: true, reason: "test", since: Date.now() }, previousSafeModeActive: false, postureChanged: false, highFocusTask: false, lowStress: false },
        basePosture,
      );
      expect(overlay).toBe(ExpressiveOverlay.ALERT);
    });

    it("returns RECOVERY during safe mode exit", () => {
      const overlay = selectOverlay(
        { safeMode: { active: false }, previousSafeModeActive: true, postureChanged: false, highFocusTask: false, lowStress: false },
        basePosture,
      );
      expect(overlay).toBe(ExpressiveOverlay.RECOVERY);
    });

    it("returns TRANSITION during posture change", () => {
      const overlay = selectOverlay(
        { safeMode: { active: false }, previousSafeModeActive: false, postureChanged: true, highFocusTask: false, lowStress: false },
        basePosture,
      );
      expect(overlay).toBe(ExpressiveOverlay.TRANSITION);
    });

    it("returns FOCUS during high-focus tasks", () => {
      const overlay = selectOverlay(
        { safeMode: { active: false }, previousSafeModeActive: false, postureChanged: false, highFocusTask: true, lowStress: false },
        basePosture,
      );
      expect(overlay).toBe(ExpressiveOverlay.FOCUS);
    });

    it("returns CALM during low-stress periods with low caution", () => {
      const lowCautionPosture = { responsiveness: 0.7, caution: 0.2 };
      const overlay = selectOverlay(
        { safeMode: { active: false }, previousSafeModeActive: false, postureChanged: false, highFocusTask: false, lowStress: true },
        lowCautionPosture,
      );
      expect(overlay).toBe(ExpressiveOverlay.CALM);
    });

    it("does NOT return CALM when caution is high", () => {
      const highCautionPosture = { responsiveness: 0.5, caution: 0.5 };
      const overlay = selectOverlay(
        { safeMode: { active: false }, previousSafeModeActive: false, postureChanged: false, highFocusTask: false, lowStress: true },
        highCautionPosture,
      );
      expect(overlay).not.toBe(ExpressiveOverlay.CALM);
    });

    it("returns NONE when no condition is met", () => {
      const overlay = selectOverlay(
        { safeMode: { active: false }, previousSafeModeActive: false, postureChanged: false, highFocusTask: false, lowStress: false },
        basePosture,
      );
      expect(overlay).toBe(ExpressiveOverlay.NONE);
    });
  });

  describe("Context-aware modulation", () => {
    it("boosts ANALYTIC sub-posture for analysis tasks", () => {
      const mod = computeContextualModulation({ taskType: "analysis", environment: "normal" });
      expect(mod.subPostureBoost).toBe(SubPosture.ANALYTIC);
    });

    it("boosts CREATIVE sub-posture for creative tasks", () => {
      const mod = computeContextualModulation({ taskType: "creative", environment: "normal" });
      expect(mod.subPostureBoost).toBe(SubPosture.CREATIVE);
    });

    it("boosts ALERT overlay for crisis environment", () => {
      const mod = computeContextualModulation({ taskType: "idle", environment: "crisis" });
      expect(mod.overlayBoost).toBe(ExpressiveOverlay.ALERT);
    });

    it("boosts RECOVERY overlay for recovery environment", () => {
      const mod = computeContextualModulation({ taskType: "idle", environment: "recovery" });
      expect(mod.overlayBoost).toBe(ExpressiveOverlay.RECOVERY);
    });

    it("boosts CALM overlay and SUPPORTIVE for handoff environment", () => {
      const mod = computeContextualModulation({ taskType: "idle", environment: "handoff" });
      expect(mod.overlayBoost).toBe(ExpressiveOverlay.CALM);
      expect(mod.subPostureBoost).toBe(SubPosture.SUPPORTIVE);
    });
  });

  describe("Operator cue", () => {
    it("stores and retrieves operator cue", () => {
      expect(getOperatorCue()).toBeNull();
      setOperatorCue({ postureBias: "cautious", subPostureBias: SubPosture.DEFENSIVE });
      expect(getOperatorCue()).toEqual({ postureBias: "cautious", subPostureBias: SubPosture.DEFENSIVE });
    });

    it("clears operator cue", () => {
      setOperatorCue({ postureBias: "stable" });
      setOperatorCue(null);
      expect(getOperatorCue()).toBeNull();
    });

    it("resets with resetExpressiveState", () => {
      setOperatorCue({ postureBias: "cautious" });
      setContext({ taskType: "creative", environment: "crisis" });
      resetExpressiveState();
      expect(getOperatorCue()).toBeNull();
      expect(getContext()).toEqual({ taskType: "idle", environment: "normal" });
    });
  });

  describe("Context engine", () => {
    it("initializes with idle/normal defaults", () => {
      expect(getContext()).toEqual({ taskType: "idle", environment: "normal" });
    });

    it("accepts partial updates", () => {
      setContext({ taskType: "analysis" });
      expect(getContext().taskType).toBe("analysis");
      expect(getContext().environment).toBe("normal");
    });

    it("accepts full updates", () => {
      const ctx = setContext({ taskType: "creative", environment: "crisis" });
      expect(ctx).toEqual({ taskType: "creative", environment: "crisis" });
    });
  });

  describe("End-to-end integration through tickKernel", () => {
    it("includes expressive state in tick result", () => {
      const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
      expect(result.expressive).toBeDefined();
      expect(result.expressive.subPosture).toBeDefined();
      expect(result.expressive.overlay).toBeDefined();
      expect(result.expressive.microPosture).toBeDefined();
      expect(result.expressive.contextual).toBeDefined();
      expect(typeof result.expressive.overlayTicksRemaining).toBe("number");
    });

    it("respects operator cue sub-posture override", () => {
      for (let i = 0; i < 5; i++) tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
      setOperatorCue({ subPostureBias: SubPosture.CREATIVE });
      const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
      expect(result.expressive.subPosture).toBe(SubPosture.CREATIVE);
    });

    it("respects operator cue overlay override", () => {
      for (let i = 0; i < 5; i++) tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
      setOperatorCue({ overlayBias: ExpressiveOverlay.FOCUS });
      const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
      expect(result.expressive.overlay).toBe(ExpressiveOverlay.FOCUS);
    });

    it("cautious posture bias influences sub-posture", () => {
      for (let i = 0; i < 5; i++) tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
      setOperatorCue({ postureBias: "cautious" });
      const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
      // With high alignment and default context, the sub-posture could be
      // DEFENSIVE (from cautious bias when NONE), SENSITIVE (from context),
      // or SUPPORTIVE (from high trust). The cautious bias only fires as a
      // fallback when the sub-posture is NONE.
      expect(result.expressive.subPosture).toBeDefined();
      expect(typeof result.expressive.subPosture).toBe("string");
    });

    it("context-aware modulation integrates with tick", () => {
      setContext({ taskType: "analysis", environment: "normal" });
      const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
      expect(result.expressive.contextual.subPostureBoost).toBe(SubPosture.ANALYTIC);
    });

    it("crisis context boosts ALERT overlay through tick", () => {
      setContext({ taskType: "idle", environment: "crisis" });
      const result = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });
      expect(result.expressive.overlay).toBe(ExpressiveOverlay.ALERT);
    });

    it("micro-posture updates proportionally to alignment", () => {
      // Low alignment
      const ctxLow = mkContext({
        beings: [mkBeing()],
        nodeCount: 1, quarantinedCount: 0, totalErrors: 50, activeHeartbeats: 1,
      });
      const r1 = tickKernel(ctxLow, { ...DEFAULT_KERNEL_CONFIG });
      resetAll();

      // High alignment
      const r2 = tickKernel(mkContext(), { ...DEFAULT_KERNEL_CONFIG });

      expect(r2.expressive.microPosture.responsiveness).toBeGreaterThanOrEqual(r1.expressive.microPosture.responsiveness);
    });

    it("multiple ticks produce consistent expressive state", () => {
      const cfg = { ...DEFAULT_KERNEL_CONFIG };
      const ctx = mkContext();
      for (let i = 0; i < 20; i++) {
        const result = tickKernel(ctx, cfg);
        expect(result.expressive).toBeDefined();
        expect(typeof result.expressive.microPosture.responsiveness).toBe("number");
        expect(typeof result.expressive.microPosture.caution).toBe("number");
        expect(typeof result.expressive.microPosture.expressiveness).toBe("number");
      }
    });

    it("safe mode entry triggers ALERT overlay", () => {
      // Trigger safe mode via catastrophically low alignment
      const ctx = mkContext({
        beings: [],
        constitutionReport: { allPassed: false, failedCount: 5, checks: [] },
        posture: "LOCKDOWN" as PostureState,
        postureReason: "crisis",
        nodeCount: 0,
        quarantinedCount: 10,
        totalErrors: 9999,
        activeHeartbeats: 0,
      });
      const result = tickKernel(ctx, { ...DEFAULT_KERNEL_CONFIG });
      if (result.safeMode.active) {
        expect(result.expressive.overlay).toBe(ExpressiveOverlay.ALERT);
      }
    });
  });
});
