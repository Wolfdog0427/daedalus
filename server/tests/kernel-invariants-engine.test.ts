import { validateInvariants } from "../../shared/daedalus/kernelInvariantsEngine";
import type { KernelState } from "../../shared/daedalus/governanceKernel";
import { KERNEL_IDLE } from "../../shared/daedalus/governanceKernel";
import type { FabricDashboard } from "../../shared/daedalus/governanceFabric";
import { FABRIC_DASHBOARD_IDLE } from "../../shared/daedalus/governanceFabric";
import type { AdaptationTuning } from "../../shared/daedalus/sceneAdaptation";
import { POST_AUTONOMY_DEFAULTS } from "../../shared/daedalus/postAutonomy";

function mkKernel(overrides: Partial<KernelState> = {}): KernelState {
  return { ...KERNEL_IDLE, ...overrides };
}

function mkDashboard(overrides: Partial<FabricDashboard> = {}): FabricDashboard {
  return { ...FABRIC_DASHBOARD_IDLE, ...overrides };
}

describe("validateInvariants", () => {
  it("all pass in idle state", () => {
    const report = validateInvariants(KERNEL_IDLE, FABRIC_DASHBOARD_IDLE, {});
    expect(report.allPassed).toBe(true);
    expect(report.failedCount).toBe(0);
    expect(report.checks.length).toBe(9);
    expect(report.checks.every((c) => c.passed)).toBe(true);
  });

  it("all pass with valid tuning within caps", () => {
    const tuning: AdaptationTuning = {
      governorCooldownMs: 800,
      grammarDefaultBlendMs: 500,
    };
    const kernel = mkKernel({ status: "tuned", overrideCount: 2 });
    const report = validateInvariants(kernel, mkDashboard(), tuning);
    expect(report.allPassed).toBe(true);
  });

  // ── structural invariants ──

  it("operator-sovereignty always passes", () => {
    const report = validateInvariants(KERNEL_IDLE, FABRIC_DASHBOARD_IDLE, {});
    const check = report.checks.find((c) => c.name === "operator-sovereignty");
    expect(check?.passed).toBe(true);
  });

  it("no-silent-changes always passes", () => {
    const report = validateInvariants(KERNEL_IDLE, FABRIC_DASHBOARD_IDLE, {});
    const check = report.checks.find((c) => c.name === "no-silent-changes");
    expect(check?.passed).toBe(true);
  });

  it("rollback-available always passes", () => {
    const report = validateInvariants(KERNEL_IDLE, FABRIC_DASHBOARD_IDLE, {});
    const check = report.checks.find((c) => c.name === "rollback-available");
    expect(check?.passed).toBe(true);
  });

  it("deterministic-merge always passes", () => {
    const report = validateInvariants(KERNEL_IDLE, FABRIC_DASHBOARD_IDLE, {});
    const check = report.checks.find((c) => c.name === "deterministic-merge");
    expect(check?.passed).toBe(true);
  });

  it("no-recursive-governance always passes", () => {
    const report = validateInvariants(KERNEL_IDLE, FABRIC_DASHBOARD_IDLE, {});
    const check = report.checks.find((c) => c.name === "no-recursive-governance");
    expect(check?.passed).toBe(true);
  });

  // ── runtime invariants ──

  it("single-proposal-bounded passes when pendingCount <= 5", () => {
    const kernel = mkKernel({ pendingCount: 5 });
    const report = validateInvariants(kernel, mkDashboard(), {});
    const check = report.checks.find((c) => c.name === "single-proposal-bounded");
    expect(check?.passed).toBe(true);
  });

  it("single-proposal-bounded fails when pendingCount > 5", () => {
    const kernel = mkKernel({ pendingCount: 6 });
    const report = validateInvariants(kernel, mkDashboard(), {});
    const check = report.checks.find((c) => c.name === "single-proposal-bounded");
    expect(check?.passed).toBe(false);
    expect(report.allPassed).toBe(false);
    expect(report.failedCount).toBe(1);
  });

  it("bounded-overrides passes when overrideCount <= 6", () => {
    const kernel = mkKernel({ overrideCount: 6 });
    const report = validateInvariants(kernel, mkDashboard(), {});
    const check = report.checks.find((c) => c.name === "bounded-overrides");
    expect(check?.passed).toBe(true);
  });

  it("bounded-overrides fails when overrideCount > 6", () => {
    const kernel = mkKernel({ overrideCount: 7 });
    const report = validateInvariants(kernel, mkDashboard(), {});
    const check = report.checks.find((c) => c.name === "bounded-overrides");
    expect(check?.passed).toBe(false);
  });

  it("caps-enforced passes when all tuning is within bounds", () => {
    const tuning: AdaptationTuning = {
      governorCooldownMs: POST_AUTONOMY_DEFAULTS.caps.governorCooldownMs[0],
      grammarDefaultBlendMs: POST_AUTONOMY_DEFAULTS.caps.grammarDefaultBlendMs[1],
    };
    const report = validateInvariants(KERNEL_IDLE, mkDashboard(), tuning);
    const check = report.checks.find((c) => c.name === "caps-enforced");
    expect(check?.passed).toBe(true);
  });

  it("caps-enforced fails when a value exceeds max", () => {
    const tuning: AdaptationTuning = { governorCooldownMs: 99999 };
    const report = validateInvariants(KERNEL_IDLE, mkDashboard(), tuning);
    const check = report.checks.find((c) => c.name === "caps-enforced");
    expect(check?.passed).toBe(false);
  });

  it("caps-enforced fails when a value is below min", () => {
    const tuning: AdaptationTuning = { grammarDefaultBlendMs: 1 };
    const report = validateInvariants(KERNEL_IDLE, mkDashboard(), tuning);
    const check = report.checks.find((c) => c.name === "caps-enforced");
    expect(check?.passed).toBe(false);
  });

  it("caps-enforced passes when tuning is empty", () => {
    const report = validateInvariants(KERNEL_IDLE, mkDashboard(), {});
    const check = report.checks.find((c) => c.name === "caps-enforced");
    expect(check?.passed).toBe(true);
  });

  it("no-escalation-leak passes when escalation and status agree", () => {
    const kernel = mkKernel({ status: "escalated" });
    const dashboard = mkDashboard({ escalationDetected: true });
    const report = validateInvariants(kernel, dashboard, {});
    const check = report.checks.find((c) => c.name === "no-escalation-leak");
    expect(check?.passed).toBe(true);
  });

  it("no-escalation-leak fails when escalation detected but status is clean", () => {
    const kernel = mkKernel({ status: "clean" });
    const dashboard = mkDashboard({ escalationDetected: true });
    const report = validateInvariants(kernel, dashboard, {});
    const check = report.checks.find((c) => c.name === "no-escalation-leak");
    expect(check?.passed).toBe(false);
  });

  it("no-escalation-leak fails when health is overloaded but status is tuned", () => {
    const kernel = mkKernel({ status: "tuned" });
    const dashboard = mkDashboard({
      health: { label: "overloaded", totalDecisions: 20, approvals: 10, rejections: 10, decisionRate: 15 },
    });
    const report = validateInvariants(kernel, dashboard, {});
    const check = report.checks.find((c) => c.name === "no-escalation-leak");
    expect(check?.passed).toBe(false);
  });

  it("no-escalation-leak passes when health is stable and status is clean", () => {
    const report = validateInvariants(KERNEL_IDLE, FABRIC_DASHBOARD_IDLE, {});
    const check = report.checks.find((c) => c.name === "no-escalation-leak");
    expect(check?.passed).toBe(true);
  });

  // ── aggregate ──

  it("counts multiple failures correctly", () => {
    const kernel = mkKernel({ pendingCount: 10, overrideCount: 10 });
    const tuning: AdaptationTuning = { governorCooldownMs: 99999 };
    const report = validateInvariants(kernel, mkDashboard(), tuning);
    expect(report.allPassed).toBe(false);
    expect(report.failedCount).toBe(3);
  });

  it("uses custom caps when provided", () => {
    const caps = { ...POST_AUTONOMY_DEFAULTS.caps, governorCooldownMs: [500, 600] as [number, number] };
    const tuning: AdaptationTuning = { governorCooldownMs: 700 };
    const report = validateInvariants(KERNEL_IDLE, mkDashboard(), tuning, caps);
    const check = report.checks.find((c) => c.name === "caps-enforced");
    expect(check?.passed).toBe(false);
  });
});
