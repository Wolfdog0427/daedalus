import { computeCrownState } from "../../shared/daedalus/kernelCrownEngine";
import type { KernelHaloSnapshot } from "../../shared/daedalus/kernelHalo";
import { HALO_IDLE } from "../../shared/daedalus/kernelHalo";

function mkHalo(overrides: Partial<KernelHaloSnapshot> = {}): KernelHaloSnapshot {
  return Object.freeze({ ...HALO_IDLE, ...overrides });
}

describe("computeCrownState", () => {
  // ── symbol ──

  it("returns serene for clean nominal state", () => {
    const crown = computeCrownState(mkHalo());
    expect(crown.symbol).toBe("serene");
  });

  it("returns attentive when kernel is tuned", () => {
    const crown = computeCrownState(mkHalo({ kernelStatus: "tuned" }));
    expect(crown.symbol).toBe("attentive");
  });

  it("returns vigilant when kernel is escalated", () => {
    const crown = computeCrownState(mkHalo({ kernelStatus: "escalated" }));
    expect(crown.symbol).toBe("vigilant");
  });

  it("returns vigilant when there are pending proposals", () => {
    const crown = computeCrownState(mkHalo({ pendingCount: 2 }));
    expect(crown.symbol).toBe("vigilant");
  });

  it("returns shielded when shell is degraded", () => {
    const crown = computeCrownState(mkHalo({ shellStatus: "degraded" }));
    expect(crown.symbol).toBe("shielded");
  });

  it("shielded takes priority over escalated", () => {
    const crown = computeCrownState(mkHalo({
      shellStatus: "degraded",
      kernelStatus: "escalated",
    }));
    expect(crown.symbol).toBe("shielded");
  });

  it("vigilant takes priority over attentive", () => {
    const crown = computeCrownState(mkHalo({
      kernelStatus: "tuned",
      pendingCount: 1,
    }));
    expect(crown.symbol).toBe("vigilant");
  });

  // ── glow ──

  it("serene has low glow", () => {
    const crown = computeCrownState(mkHalo());
    expect(crown.glow).toBe(0.3);
  });

  it("attentive has medium glow", () => {
    const crown = computeCrownState(mkHalo({ kernelStatus: "tuned" }));
    expect(crown.glow).toBe(0.6);
  });

  it("vigilant has high glow", () => {
    const crown = computeCrownState(mkHalo({ kernelStatus: "escalated" }));
    expect(crown.glow).toBe(0.9);
  });

  it("shielded has dim glow", () => {
    const crown = computeCrownState(mkHalo({ shellStatus: "degraded" }));
    expect(crown.glow).toBe(0.15);
  });

  // ── pulse ──

  it("no pulse with zero pending", () => {
    const crown = computeCrownState(mkHalo());
    expect(crown.pulse).toBe(0);
  });

  it("pulse scales with pending count", () => {
    const crown = computeCrownState(mkHalo({ pendingCount: 2 }));
    expect(crown.pulse).toBeCloseTo(0.6);
  });

  it("pulse caps at 1", () => {
    const crown = computeCrownState(mkHalo({ pendingCount: 10 }));
    expect(crown.pulse).toBe(1);
  });

  it("degraded forces pulse to 0.5 regardless of pending", () => {
    const crown = computeCrownState(mkHalo({
      shellStatus: "degraded",
      pendingCount: 0,
    }));
    expect(crown.pulse).toBe(0.5);
  });

  // ── stability ──

  it("full stability with no overrides or failures", () => {
    const crown = computeCrownState(mkHalo());
    expect(crown.stability).toBe(1);
  });

  it("reduces stability with overrides", () => {
    const crown = computeCrownState(mkHalo({ overrideCount: 5 }));
    expect(crown.stability).toBeCloseTo(0.6);
  });

  it("reduces stability with failed invariants", () => {
    const crown = computeCrownState(mkHalo({
      failedInvariants: Object.freeze(["caps-enforced", "bounded-overrides"]),
      invariantsPassed: false,
    }));
    expect(crown.stability).toBeCloseTo(0.7);
  });

  it("reduces stability when capping is applied", () => {
    const crown = computeCrownState(mkHalo({ cappingApplied: true }));
    expect(crown.stability).toBeCloseTo(0.9);
  });

  it("stability compounds all penalties", () => {
    const crown = computeCrownState(mkHalo({
      overrideCount: 4,
      failedInvariants: Object.freeze(["caps-enforced"]),
      invariantsPassed: false,
      cappingApplied: true,
    }));
    // 1 - (4*0.08) - (1*0.15) - 0.1 = 1 - 0.32 - 0.15 - 0.1 = 0.43
    expect(crown.stability).toBeCloseTo(0.43);
  });

  it("stability clamps to 0", () => {
    const crown = computeCrownState(mkHalo({
      overrideCount: 6,
      failedInvariants: Object.freeze(["a", "b", "c", "d"]),
      invariantsPassed: false,
      cappingApplied: true,
    }));
    // 1 - (6*0.08) - (4*0.15) - 0.1 = 1 - 0.48 - 0.60 - 0.1 = -0.18 → 0
    expect(crown.stability).toBe(0);
  });

  // ── frozen ──

  it("produces a frozen object", () => {
    const crown = computeCrownState(mkHalo());
    expect(Object.isFrozen(crown)).toBe(true);
  });
});
