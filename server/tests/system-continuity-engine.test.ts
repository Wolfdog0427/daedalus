import {
  computeIdentityContinuity,
  computeStateContinuity,
  computeExpressiveContinuity,
  computeTemporalContinuity,
  computeComposite,
  deriveContinuityHealth,
  computeSystemContinuity,
  type SystemContinuityInput,
} from "../../shared/daedalus/systemContinuityEngine";
import { SYSTEM_CONTINUITY_IDLE } from "../../shared/daedalus/systemContinuity";

describe("computeIdentityContinuity", () => {
  it("returns 0 when no beings", () => {
    expect(computeIdentityContinuity(0.8, 0, 10)).toBe(0);
  });

  it("blends stability (60%) with streak factor (40%)", () => {
    const val = computeIdentityContinuity(1, 2, 25);
    expect(val).toBeCloseTo(1 * 0.6 + 1 * 0.4);
  });

  it("streak caps at 25 for the factor", () => {
    const a = computeIdentityContinuity(0.5, 2, 25);
    const b = computeIdentityContinuity(0.5, 2, 100);
    expect(b).toBeCloseTo(a);
  });

  it("increases with stability", () => {
    const low = computeIdentityContinuity(0.3, 2, 10);
    const high = computeIdentityContinuity(0.9, 2, 10);
    expect(high).toBeGreaterThan(low);
  });

  it("clamps to [0,1]", () => {
    expect(computeIdentityContinuity(2, 5, 100)).toBeLessThanOrEqual(1);
  });
});

describe("computeStateContinuity", () => {
  it("blends orchestration stability (70%) with blend (30%)", () => {
    expect(computeStateContinuity(1, 1)).toBeCloseTo(1);
    expect(computeStateContinuity(0, 0)).toBeCloseTo(0);
  });

  it("weights stability more heavily", () => {
    const highStab = computeStateContinuity(0.8, 0.2);
    const highBlend = computeStateContinuity(0.2, 0.8);
    expect(highStab).toBeGreaterThan(highBlend);
  });
});

describe("computeExpressiveContinuity", () => {
  it("blends embodied continuity (60%) with motion grammar (40%)", () => {
    expect(computeExpressiveContinuity(1, 1)).toBeCloseTo(1);
    expect(computeExpressiveContinuity(0, 0)).toBeCloseTo(0);
    expect(computeExpressiveContinuity(0.5, 0.5)).toBeCloseTo(0.5);
  });

  it("weights embodied continuity more heavily", () => {
    const highEmbodied = computeExpressiveContinuity(0.8, 0.2);
    const highMotion = computeExpressiveContinuity(0.2, 0.8);
    expect(highEmbodied).toBeGreaterThan(highMotion);
  });
});

describe("computeTemporalContinuity", () => {
  it("uses timeline momentum at 80% weight", () => {
    expect(computeTemporalContinuity(1, false)).toBeCloseTo(0.8);
  });

  it("adds persistence bonus of 0.2 when restored", () => {
    expect(computeTemporalContinuity(1, true)).toBeCloseTo(1);
    expect(computeTemporalContinuity(0, true)).toBeCloseTo(0.2);
  });

  it("returns 0 with no momentum and no restore", () => {
    expect(computeTemporalContinuity(0, false)).toBeCloseTo(0);
  });
});

describe("computeComposite", () => {
  it("returns 1 when all axes are 1", () => {
    expect(computeComposite(1, 1, 1, 1)).toBeCloseTo(1);
  });

  it("returns 0 when all axes are 0", () => {
    expect(computeComposite(0, 0, 0, 0)).toBeCloseTo(0);
  });

  it("weights identity and state (30% each) more than expressive and temporal (20% each)", () => {
    const identityHeavy = computeComposite(1, 0, 0, 0);
    const temporalHeavy = computeComposite(0, 0, 0, 1);
    expect(identityHeavy).toBeGreaterThan(temporalHeavy);
  });
});

describe("deriveContinuityHealth", () => {
  it("returns healthy above 0.7", () => {
    expect(deriveContinuityHealth(0.8)).toBe("healthy");
    expect(deriveContinuityHealth(1)).toBe("healthy");
  });

  it("returns shifting between 0.4 and 0.7", () => {
    expect(deriveContinuityHealth(0.5)).toBe("shifting");
    expect(deriveContinuityHealth(0.7)).toBe("shifting");
  });

  it("returns fragile at or below 0.4", () => {
    expect(deriveContinuityHealth(0.4)).toBe("fragile");
    expect(deriveContinuityHealth(0)).toBe("fragile");
  });
});

describe("computeSystemContinuity", () => {
  const base: SystemContinuityInput = {
    beingStability: 0.8,
    beingCount: 2,
    bestStreak: 12,
    driftSignalCount: 0,
    anchorBeingId: "alpha",
    orchestrationStability: 0.9,
    continuityBlend: 0.7,
    embodiedContinuity: 0.8,
    motionGrammar: 0.6,
    timelineMomentum: 0.5,
    persistenceRestored: true,
  };

  it("produces a frozen snapshot", () => {
    const snap = computeSystemContinuity(base);
    expect(Object.isFrozen(snap)).toBe(true);
  });

  it("computes all four axes", () => {
    const snap = computeSystemContinuity(base);
    expect(snap.identity).toBeGreaterThan(0);
    expect(snap.state).toBeGreaterThan(0);
    expect(snap.expressive).toBeGreaterThan(0);
    expect(snap.temporal).toBeGreaterThan(0);
  });

  it("computes composite from the four axes", () => {
    const snap = computeSystemContinuity(base);
    expect(snap.composite).toBeCloseTo(
      snap.identity * 0.3 + snap.state * 0.3 + snap.expressive * 0.2 + snap.temporal * 0.2,
    );
  });

  it("derives health from composite", () => {
    const snap = computeSystemContinuity(base);
    expect(snap.health).toBe("healthy");
  });

  it("forwards driftSignalCount and anchorBeingId", () => {
    const snap = computeSystemContinuity({ ...base, driftSignalCount: 3, anchorBeingId: "beta" });
    expect(snap.driftSignalCount).toBe(3);
    expect(snap.anchorBeingId).toBe("beta");
  });

  it("reports fragile when all inputs are low", () => {
    const snap = computeSystemContinuity({
      ...base,
      beingStability: 0.1,
      bestStreak: 0,
      orchestrationStability: 0.1,
      continuityBlend: 0.1,
      embodiedContinuity: 0.1,
      motionGrammar: 0.1,
      timelineMomentum: 0,
      persistenceRestored: false,
    });
    expect(snap.health).toBe("fragile");
  });

  it("returns zero identity with no beings", () => {
    const snap = computeSystemContinuity({ ...base, beingCount: 0 });
    expect(snap.identity).toBe(0);
  });
});

describe("SYSTEM_CONTINUITY_IDLE", () => {
  it("is frozen", () => {
    expect(Object.isFrozen(SYSTEM_CONTINUITY_IDLE)).toBe(true);
  });

  it("has healthy defaults at full continuity", () => {
    expect(SYSTEM_CONTINUITY_IDLE.identity).toBe(1);
    expect(SYSTEM_CONTINUITY_IDLE.state).toBe(1);
    expect(SYSTEM_CONTINUITY_IDLE.composite).toBe(1);
    expect(SYSTEM_CONTINUITY_IDLE.health).toBe("healthy");
  });
});
