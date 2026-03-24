import { computeThroneView } from "../../shared/daedalus/kernelThroneEngine";
import type { KernelHaloSnapshot } from "../../shared/daedalus/kernelHalo";
import type { CrownState } from "../../shared/daedalus/kernelCrown";
import { HALO_IDLE } from "../../shared/daedalus/kernelHalo";
import { CROWN_IDLE } from "../../shared/daedalus/kernelCrown";

function mkHalo(overrides: Partial<KernelHaloSnapshot> = {}): KernelHaloSnapshot {
  return Object.freeze({ ...HALO_IDLE, ...overrides });
}

function mkCrown(overrides: Partial<CrownState> = {}): CrownState {
  return Object.freeze({ ...CROWN_IDLE, ...overrides });
}

describe("computeThroneView", () => {
  it("returns idle-equivalent for idle inputs", () => {
    const throne = computeThroneView(HALO_IDLE, CROWN_IDLE);
    expect(throne.symbol).toBe("serene");
    expect(throne.glow).toBe(0.3);
    expect(throne.pulse).toBe(0);
    expect(throne.stability).toBe(1);
    expect(throne.shellStatus).toBe("nominal");
    expect(throne.kernelStatus).toBe("clean");
    expect(throne.overrideCount).toBe(0);
    expect(throne.pendingCount).toBe(0);
    expect(throne.invariantsPassed).toBe(true);
  });

  it("takes symbol from crown", () => {
    const throne = computeThroneView(mkHalo(), mkCrown({ symbol: "vigilant" }));
    expect(throne.symbol).toBe("vigilant");
  });

  it("takes glow from crown", () => {
    const throne = computeThroneView(mkHalo(), mkCrown({ glow: 0.9 }));
    expect(throne.glow).toBe(0.9);
  });

  it("takes pulse from crown", () => {
    const throne = computeThroneView(mkHalo(), mkCrown({ pulse: 0.6 }));
    expect(throne.pulse).toBe(0.6);
  });

  it("takes stability from crown", () => {
    const throne = computeThroneView(mkHalo(), mkCrown({ stability: 0.4 }));
    expect(throne.stability).toBe(0.4);
  });

  it("takes shellStatus from halo", () => {
    const throne = computeThroneView(mkHalo({ shellStatus: "degraded" }), mkCrown());
    expect(throne.shellStatus).toBe("degraded");
  });

  it("takes kernelStatus from halo", () => {
    const throne = computeThroneView(mkHalo({ kernelStatus: "escalated" }), mkCrown());
    expect(throne.kernelStatus).toBe("escalated");
  });

  it("takes overrideCount and activeOverrides from halo", () => {
    const overrides = Object.freeze(["governorCooldownMs", "grammarDefaultBlendMs"]);
    const throne = computeThroneView(
      mkHalo({ overrideCount: 2, activeOverrides: overrides }),
      mkCrown(),
    );
    expect(throne.overrideCount).toBe(2);
    expect(throne.activeOverrides).toEqual(["governorCooldownMs", "grammarDefaultBlendMs"]);
  });

  it("takes pendingCount from halo", () => {
    const throne = computeThroneView(mkHalo({ pendingCount: 3 }), mkCrown());
    expect(throne.pendingCount).toBe(3);
  });

  it("takes activeTierCount from halo", () => {
    const throne = computeThroneView(mkHalo({ activeTierCount: 4 }), mkCrown());
    expect(throne.activeTierCount).toBe(4);
  });

  it("takes cappingApplied from halo", () => {
    const throne = computeThroneView(mkHalo({ cappingApplied: true }), mkCrown());
    expect(throne.cappingApplied).toBe(true);
  });

  it("takes invariant metrics from halo", () => {
    const throne = computeThroneView(
      mkHalo({ invariantsHeld: 7, invariantsTotal: 9, invariantsPassed: false }),
      mkCrown(),
    );
    expect(throne.invariantsHeld).toBe(7);
    expect(throne.invariantsTotal).toBe(9);
    expect(throne.invariantsPassed).toBe(false);
  });

  it("produces a frozen object", () => {
    const throne = computeThroneView(HALO_IDLE, CROWN_IDLE);
    expect(Object.isFrozen(throne)).toBe(true);
  });

  it("combines full halo and crown into one coherent view", () => {
    const halo = mkHalo({
      shellStatus: "degraded",
      kernelStatus: "escalated",
      overrideCount: 3,
      pendingCount: 2,
      activeTierCount: 5,
      cappingApplied: true,
      invariantsHeld: 6,
      invariantsTotal: 9,
      invariantsPassed: false,
    });
    const crown = mkCrown({
      symbol: "shielded",
      glow: 0.15,
      pulse: 0.5,
      stability: 0.3,
    });
    const throne = computeThroneView(halo, crown);

    expect(throne.symbol).toBe("shielded");
    expect(throne.glow).toBe(0.15);
    expect(throne.shellStatus).toBe("degraded");
    expect(throne.kernelStatus).toBe("escalated");
    expect(throne.overrideCount).toBe(3);
    expect(throne.pendingCount).toBe(2);
    expect(throne.invariantsPassed).toBe(false);
    expect(throne.stability).toBe(0.3);
  });
});
