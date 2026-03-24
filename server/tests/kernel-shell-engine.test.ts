import { computeShellState } from "../../shared/daedalus/kernelShellEngine";
import { KERNEL_IDLE } from "../../shared/daedalus/governanceKernel";
import { FABRIC_DASHBOARD_IDLE } from "../../shared/daedalus/governanceFabric";
import type { FabricDashboard } from "../../shared/daedalus/governanceFabric";
import type { AdaptationTuning } from "../../shared/daedalus/sceneAdaptation";
import { POST_AUTONOMY_DEFAULTS } from "../../shared/daedalus/postAutonomy";

function mkDashboard(overrides: Partial<FabricDashboard> = {}): FabricDashboard {
  return { ...FABRIC_DASHBOARD_IDLE, ...overrides };
}

describe("computeShellState", () => {
  it("returns nominal with idle inputs", () => {
    const result = computeShellState({}, FABRIC_DASHBOARD_IDLE);
    expect(result.shellStatus).toBe("nominal");
    expect(result.kernel).toEqual(KERNEL_IDLE);
    expect(result.invariants.allPassed).toBe(true);
  });

  it("returns nominal with valid tuning", () => {
    const tuning: AdaptationTuning = { governorCooldownMs: 800 };
    const result = computeShellState(tuning, mkDashboard());
    expect(result.shellStatus).toBe("nominal");
    expect(result.kernel.status).toBe("tuned");
    expect(result.kernel.overrideCount).toBe(1);
  });

  it("returns nominal when escalation and kernel status agree", () => {
    const dashboard = mkDashboard({ escalationDetected: true });
    const result = computeShellState({}, dashboard);
    expect(result.shellStatus).toBe("nominal");
    expect(result.kernel.status).toBe("escalated");
  });

  it("returns degraded when tuning exceeds cap bounds", () => {
    const tuning: AdaptationTuning = { governorCooldownMs: 99999 };
    const result = computeShellState(tuning, mkDashboard());
    expect(result.shellStatus).toBe("degraded");
    expect(result.kernel).toEqual(KERNEL_IDLE);
    expect(result.invariants.allPassed).toBe(false);
  });

  it("returns degraded when tuning is below cap minimum", () => {
    const tuning: AdaptationTuning = { grammarDefaultBlendMs: 1 };
    const result = computeShellState(tuning, mkDashboard());
    expect(result.shellStatus).toBe("degraded");
    expect(result.kernel).toEqual(KERNEL_IDLE);
  });

  it("degraded state still includes the invariant report", () => {
    const tuning: AdaptationTuning = { governorCooldownMs: 99999 };
    const result = computeShellState(tuning, mkDashboard());
    expect(result.invariants.failedCount).toBeGreaterThan(0);
    const failed = result.invariants.checks.filter((c) => !c.passed);
    expect(failed.some((c) => c.name === "caps-enforced")).toBe(true);
  });

  it("uses custom caps when provided", () => {
    const caps = {
      ...POST_AUTONOMY_DEFAULTS.caps,
      governorCooldownMs: [500, 600] as [number, number],
    };
    const tuning: AdaptationTuning = { governorCooldownMs: 700 };
    const result = computeShellState(tuning, mkDashboard(), caps);
    expect(result.shellStatus).toBe("degraded");
  });

  it("passes through kernel state when nominal", () => {
    const tuning: AdaptationTuning = {
      governorCooldownMs: 800,
      grammarDefaultBlendMs: 500,
    };
    const dashboard = mkDashboard({ pendingCount: 2 });
    const result = computeShellState(tuning, dashboard);
    expect(result.shellStatus).toBe("nominal");
    expect(result.kernel.overrideCount).toBe(2);
    expect(result.kernel.pendingCount).toBe(2);
  });

  it("nominal preserves escalated kernel status", () => {
    const dashboard = mkDashboard({
      escalationDetected: true,
      activeTierCount: 5,
    });
    const result = computeShellState({}, dashboard);
    expect(result.shellStatus).toBe("nominal");
    expect(result.kernel.status).toBe("escalated");
    expect(result.kernel.activeTierCount).toBe(5);
  });

  it("reports all 9 invariant checks in both nominal and degraded", () => {
    const nominal = computeShellState({}, mkDashboard());
    expect(nominal.invariants.checks.length).toBe(9);

    const degraded = computeShellState(
      { governorCooldownMs: 99999 },
      mkDashboard(),
    );
    expect(degraded.invariants.checks.length).toBe(9);
  });

  it("degraded prevents corrupted kernel from leaking", () => {
    const tuning: AdaptationTuning = { governorCooldownMs: 99999 };
    const dashboard = mkDashboard({ activeTierCount: 3, pendingCount: 2 });
    const result = computeShellState(tuning, dashboard);
    expect(result.shellStatus).toBe("degraded");
    expect(result.kernel.activeTierCount).toBe(0);
    expect(result.kernel.pendingCount).toBe(0);
    expect(result.kernel.status).toBe("clean");
  });
});
