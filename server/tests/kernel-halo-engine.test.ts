import { computeHaloSnapshot } from "../../shared/daedalus/kernelHaloEngine";
import type { KernelShellState } from "../../shared/daedalus/kernelShell";
import { KERNEL_IDLE } from "../../shared/daedalus/governanceKernel";
import { INVARIANT_REPORT_CLEAN } from "../../shared/daedalus/kernelInvariants";
import type { KernelState } from "../../shared/daedalus/governanceKernel";
import type { InvariantReport, InvariantCheck } from "../../shared/daedalus/kernelInvariants";

function mkShell(overrides: Partial<KernelShellState> = {}): KernelShellState {
  return {
    shellStatus: "nominal",
    kernel: KERNEL_IDLE,
    invariants: INVARIANT_REPORT_CLEAN,
    ...overrides,
  };
}

function mkKernel(overrides: Partial<KernelState> = {}): KernelState {
  return { ...KERNEL_IDLE, ...overrides };
}

function mkInvariants(overrides: Partial<InvariantReport> & { checks?: InvariantCheck[] } = {}): InvariantReport {
  return {
    allPassed: true,
    checks: [],
    failedCount: 0,
    ...overrides,
  };
}

describe("computeHaloSnapshot", () => {
  it("returns idle-equivalent for idle shell state", () => {
    const halo = computeHaloSnapshot(mkShell());
    expect(halo.shellStatus).toBe("nominal");
    expect(halo.kernelStatus).toBe("clean");
    expect(halo.overrideCount).toBe(0);
    expect(halo.activeOverrides).toEqual([]);
    expect(halo.activeTierCount).toBe(0);
    expect(halo.pendingCount).toBe(0);
    expect(halo.cappingApplied).toBe(false);
    expect(halo.invariantsPassed).toBe(true);
    expect(halo.failedInvariants).toEqual([]);
  });

  it("passes through shell status", () => {
    const halo = computeHaloSnapshot(mkShell({ shellStatus: "degraded" }));
    expect(halo.shellStatus).toBe("degraded");
  });

  it("passes through kernel status", () => {
    const halo = computeHaloSnapshot(mkShell({
      kernel: mkKernel({ status: "escalated" }),
    }));
    expect(halo.kernelStatus).toBe("escalated");
  });

  it("passes through override count and active overrides", () => {
    const halo = computeHaloSnapshot(mkShell({
      kernel: mkKernel({
        overrideCount: 3,
        activeOverrides: ["governorCooldownMs", "grammarDefaultBlendMs", "narrativeMinIntervalMs"],
      }),
    }));
    expect(halo.overrideCount).toBe(3);
    expect(halo.activeOverrides).toEqual([
      "governorCooldownMs",
      "grammarDefaultBlendMs",
      "narrativeMinIntervalMs",
    ]);
  });

  it("passes through activeTierCount, pendingCount, cappingApplied", () => {
    const halo = computeHaloSnapshot(mkShell({
      kernel: mkKernel({ activeTierCount: 4, pendingCount: 2, cappingApplied: true }),
    }));
    expect(halo.activeTierCount).toBe(4);
    expect(halo.pendingCount).toBe(2);
    expect(halo.cappingApplied).toBe(true);
  });

  it("computes invariantsHeld and invariantsTotal from checks", () => {
    const checks: InvariantCheck[] = [
      { name: "operator-sovereignty", passed: true },
      { name: "caps-enforced", passed: false },
      { name: "no-escalation-leak", passed: true },
    ];
    const halo = computeHaloSnapshot(mkShell({
      invariants: mkInvariants({ checks, failedCount: 1, allPassed: false }),
    }));
    expect(halo.invariantsTotal).toBe(3);
    expect(halo.invariantsHeld).toBe(2);
    expect(halo.invariantsPassed).toBe(false);
  });

  it("collects failed invariant names", () => {
    const checks: InvariantCheck[] = [
      { name: "operator-sovereignty", passed: true },
      { name: "caps-enforced", passed: false },
      { name: "bounded-overrides", passed: false },
    ];
    const halo = computeHaloSnapshot(mkShell({
      invariants: mkInvariants({ checks, failedCount: 2, allPassed: false }),
    }));
    expect(halo.failedInvariants).toEqual(["caps-enforced", "bounded-overrides"]);
  });

  it("returns empty failedInvariants when all pass", () => {
    const checks: InvariantCheck[] = [
      { name: "operator-sovereignty", passed: true },
      { name: "rollback-available", passed: true },
    ];
    const halo = computeHaloSnapshot(mkShell({
      invariants: mkInvariants({ checks, failedCount: 0, allPassed: true }),
    }));
    expect(halo.failedInvariants).toEqual([]);
    expect(halo.invariantsPassed).toBe(true);
  });

  it("produces a frozen snapshot", () => {
    const halo = computeHaloSnapshot(mkShell());
    expect(Object.isFrozen(halo)).toBe(true);
  });

  it("produces frozen activeOverrides array", () => {
    const halo = computeHaloSnapshot(mkShell({
      kernel: mkKernel({ activeOverrides: ["governorCooldownMs"] }),
    }));
    expect(Object.isFrozen(halo.activeOverrides)).toBe(true);
  });

  it("produces frozen failedInvariants array", () => {
    const checks: InvariantCheck[] = [
      { name: "caps-enforced", passed: false },
    ];
    const halo = computeHaloSnapshot(mkShell({
      invariants: mkInvariants({ checks, failedCount: 1, allPassed: false }),
    }));
    expect(Object.isFrozen(halo.failedInvariants)).toBe(true);
  });

  it("does not leak mutable references from the original kernel", () => {
    const overrides = ["governorCooldownMs"];
    const kernel = mkKernel({ activeOverrides: overrides });
    const halo = computeHaloSnapshot(mkShell({ kernel }));
    overrides.push("grammarDefaultBlendMs");
    expect(halo.activeOverrides).toEqual(["governorCooldownMs"]);
  });
});
