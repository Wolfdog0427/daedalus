import { computeKernelState } from "../../shared/daedalus/governanceKernelEngine";
import type { AdaptationTuning } from "../../shared/daedalus/sceneAdaptation";
import type { FabricDashboard } from "../../shared/daedalus/governanceFabric";
import { FABRIC_DASHBOARD_IDLE } from "../../shared/daedalus/governanceFabric";

function mkDashboard(overrides: Partial<FabricDashboard> = {}): FabricDashboard {
  return { ...FABRIC_DASHBOARD_IDLE, ...overrides };
}

describe("computeKernelState", () => {
  it("returns clean when no overrides and no escalation", () => {
    const k = computeKernelState({}, mkDashboard());
    expect(k.status).toBe("clean");
    expect(k.overrideCount).toBe(0);
    expect(k.activeOverrides).toEqual([]);
    expect(k.activeTierCount).toBe(0);
    expect(k.pendingCount).toBe(0);
    expect(k.cappingApplied).toBe(false);
  });

  it("returns tuned when overrides are present", () => {
    const tuning: AdaptationTuning = { governorCooldownMs: 900 };
    const k = computeKernelState(tuning, mkDashboard({ activeTierCount: 1 }));
    expect(k.status).toBe("tuned");
    expect(k.overrideCount).toBe(1);
    expect(k.activeOverrides).toEqual(["governorCooldownMs"]);
  });

  it("returns escalated when escalation is detected", () => {
    const k = computeKernelState({}, mkDashboard({ escalationDetected: true }));
    expect(k.status).toBe("escalated");
  });

  it("returns escalated when health label is overloaded", () => {
    const k = computeKernelState(
      {},
      mkDashboard({
        health: {
          label: "overloaded",
          totalDecisions: 20,
          approvals: 10,
          rejections: 10,
          decisionRate: 15,
        },
      }),
    );
    expect(k.status).toBe("escalated");
  });

  it("escalated takes priority over tuned", () => {
    const tuning: AdaptationTuning = { governorCooldownMs: 900 };
    const k = computeKernelState(tuning, mkDashboard({ escalationDetected: true }));
    expect(k.status).toBe("escalated");
    expect(k.overrideCount).toBe(1);
  });

  it("counts multiple overrides correctly", () => {
    const tuning: AdaptationTuning = {
      governorCooldownMs: 900,
      grammarDefaultBlendMs: 500,
      timelineMomentumHalfLifeMs: 8000,
    };
    const k = computeKernelState(tuning, mkDashboard());
    expect(k.overrideCount).toBe(3);
    expect(k.activeOverrides).toHaveLength(3);
    expect(k.activeOverrides).toContain("governorCooldownMs");
    expect(k.activeOverrides).toContain("grammarDefaultBlendMs");
    expect(k.activeOverrides).toContain("timelineMomentumHalfLifeMs");
  });

  it("passes through activeTierCount from dashboard", () => {
    const k = computeKernelState({}, mkDashboard({ activeTierCount: 3 }));
    expect(k.activeTierCount).toBe(3);
  });

  it("passes through pendingCount from dashboard", () => {
    const k = computeKernelState({}, mkDashboard({ pendingCount: 2 }));
    expect(k.pendingCount).toBe(2);
  });

  it("passes through cappingApplied from dashboard", () => {
    const k = computeKernelState({}, mkDashboard({ cappingApplied: true }));
    expect(k.cappingApplied).toBe(true);
  });

  it("excludes undefined tuning fields from overrides", () => {
    const tuning: AdaptationTuning = {
      governorCooldownMs: 900,
      narrativeMinIntervalMs: undefined,
    };
    const k = computeKernelState(tuning, mkDashboard());
    expect(k.overrideCount).toBe(1);
    expect(k.activeOverrides).toEqual(["governorCooldownMs"]);
  });
});
